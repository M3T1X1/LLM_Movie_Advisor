import json
import os
from datetime import timedelta
from functools import wraps

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from psycopg.types.json import Jsonb

from backend.accounts.management.commands.seed_demo_data import (
    Command as SeedDemoCommand,
)
from backend.accounts.management.commands.seed_demo_data import (
    TmdbClient,
    normalize_tmdb_item,
)
from backend.accounts.services import get_business_user_id, sync_business_user


def authenticated(view):
    @wraps(view)
    def wrapped(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"detail": "Authentication required."}, status=401)
        return view(request, *args, **kwargs)

    return wrapped


def request_data(request: HttpRequest) -> dict | None:
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def iso(value):
    return value.isoformat() if value is not None else None


def json_object(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def json_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def serialize_content_rows(rows) -> list[dict]:
    return [
        {
            "id": str(row[0]),
            "tmdbId": row[1],
            "mediaType": row[2],
            "title": row[3],
            "originalTitle": row[4],
            "overview": row[5],
            "releaseDate": iso(row[6]),
            "originalLanguage": row[7],
            "posterPath": row[8],
            "voteAverage": float(row[9]) if row[9] is not None else None,
            "popularity": float(row[10]) if row[10] is not None else None,
            "metadata": json_object(row[11]),
            "tmdbRefreshedAt": iso(row[12]),
            "genres": json_list(row[13]),
        }
        for row in rows
    ]


CONTENT_SELECT = """
    SELECT
        c.id, c.tmdb_id, c.media_type::text, c.title, c.original_title,
        c.overview, c.release_date, c.original_language, c.poster_path,
        c.vote_average, c.popularity, c.metadata, c.tmdb_refreshed_at,
        COALESCE(
            jsonb_agg(
                jsonb_build_object(
                    'id', g.id::text,
                    'tmdbGenreId', g.tmdb_genre_id,
                    'name', g.name
                )
                ORDER BY g.name
            ) FILTER (WHERE g.id IS NOT NULL),
            '[]'::jsonb
        ) AS genres
    FROM content c
    LEFT JOIN content_genre cg ON cg.content_id = c.id
    LEFT JOIN genre g ON g.id = cg.genre_id
"""


def fetch_content(where_sql="", params=None, order_sql="c.popularity DESC NULLS LAST"):
    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            {CONTENT_SELECT}
            {where_sql}
            GROUP BY c.id
            ORDER BY {order_sql}
            """,
            params or [],
        )
        return serialize_content_rows(cursor.fetchall())


def serialize_conversation(row) -> dict:
    return {
        "id": str(row[0]),
        "userId": str(row[1]),
        "title": row[2],
        "createdAt": iso(row[3]),
        "updatedAt": iso(row[4]),
    }


def serialize_message(row) -> dict:
    return {
        "id": str(row[0]),
        "conversationId": str(row[1]),
        "role": row[2],
        "content": row[3],
        "sequenceNo": row[4],
        "createdAt": iso(row[5]),
    }


def serialize_interaction(row) -> dict:
    return {
        "id": str(row[0]),
        "userId": str(row[1]),
        "contentId": str(row[2]),
        "sourceCandidateId": str(row[3]) if row[3] is not None else None,
        "interactionType": row[4],
        "rating": float(row[5]) if row[5] is not None else None,
        "metadata": json_object(row[6]),
        "createdAt": iso(row[7]),
    }


@require_http_methods(["GET"])
@authenticated
def bootstrap(request: HttpRequest) -> JsonResponse:
    user_id = get_business_user_id(request.user)
    user = sync_business_user(request.user)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT user_id, semantic_summary, version, last_rebuilt_at, updated_at
            FROM user_profile
            WHERE user_id = %s
            """,
            [user_id],
        )
        profile_row = cursor.fetchone()
        cursor.execute(
            """
            SELECT id, user_id, preference_type, preference_value, polarity,
                   weight, confidence, created_at, updated_at
            FROM user_preference
            WHERE user_id = %s
            ORDER BY polarity DESC, weight DESC, id
            """,
            [user_id],
        )
        preference_rows = cursor.fetchall()
        cursor.execute(
            """
            SELECT id, user_id, title, created_at, updated_at
            FROM conversation
            WHERE user_id = %s
            ORDER BY updated_at DESC, id DESC
            """,
            [user_id],
        )
        conversation_rows = cursor.fetchall()
        conversation_ids = [row[0] for row in conversation_rows]
        if conversation_ids:
            cursor.execute(
                """
                SELECT id, conversation_id, role::text, content, sequence_no, created_at
                FROM message
                WHERE conversation_id = ANY(%s)
                ORDER BY conversation_id, sequence_no
                """,
                [conversation_ids],
            )
            message_rows = cursor.fetchall()
        else:
            message_rows = []
        cursor.execute(
            """
            SELECT id, user_id, content_id, source_candidate_id,
                   interaction_type::text, rating, metadata, created_at
            FROM interaction
            WHERE user_id = %s
            ORDER BY created_at, id
            """,
            [user_id],
        )
        interaction_rows = cursor.fetchall()

    profile = {
        "userId": str(user_id),
        "semanticSummary": profile_row[1] if profile_row else None,
        "version": profile_row[2] if profile_row else 1,
        "lastRebuiltAt": iso(profile_row[3]) if profile_row else None,
        "updatedAt": iso(profile_row[4]) if profile_row else iso(timezone.now()),
    }
    preferences = [
        {
            "id": str(row[0]),
            "userId": str(row[1]),
            "preferenceType": row[2],
            "preferenceValue": row[3],
            "polarity": row[4],
            "weight": float(row[5]),
            "confidence": float(row[6]),
            "createdAt": iso(row[7]),
            "updatedAt": iso(row[8]),
        }
        for row in preference_rows
    ]
    return JsonResponse(
        {
            "user": user,
            "semanticProfile": profile,
            "preferences": preferences,
            "conversations": [serialize_conversation(row) for row in conversation_rows],
            "messages": [serialize_message(row) for row in message_rows],
            "interactions": [
                serialize_interaction(row) for row in interaction_rows
            ],
        }
    )


@require_http_methods(["GET"])
@authenticated
def contents(request: HttpRequest) -> JsonResponse:
    return JsonResponse(fetch_content(), safe=False)


def sync_upcoming_from_tmdb():
    client = TmdbClient(
        api_key=os.environ.get("TMDB_API_KEY"),
        access_token=os.environ.get("TMDB_API_TOKEN"),
    )
    genres = client.fetch_genres()
    items = []
    for page in (1, 2):
        payload = client.get(
            "/movie/upcoming",
            language="pl-PL",
            region="PL",
            page=page,
        )
        for raw_item in payload.get("results", []):
            item = normalize_tmdb_item(raw_item, "movie")
            if item is not None:
                items.append(item)
    unique_items = list({item.tmdb_id: item for item in items}.values())
    if unique_items:
        with transaction.atomic():
            SeedDemoCommand()._seed_catalog(genres, unique_items)


@require_http_methods(["GET"])
@authenticated
def upcoming_contents(request: HttpRequest) -> JsonResponse:
    refresh = request.GET.get("refresh") == "1"
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM content
                WHERE media_type = 'movie' AND release_date >= CURRENT_DATE
                  AND tmdb_refreshed_at >= %s
            )
            """,
            [timezone.now() - timedelta(hours=12)],
        )
        has_fresh_data = cursor.fetchone()[0]
    if refresh or not has_fresh_data:
        try:
            sync_upcoming_from_tmdb()
        except Exception:
            if refresh:
                return JsonResponse(
                    {"detail": "TMDB upcoming releases are unavailable."},
                    status=503,
                )
    data = fetch_content(
        "WHERE c.media_type = 'movie' AND c.release_date >= CURRENT_DATE",
        order_sql="c.release_date, c.popularity DESC NULLS LAST",
    )
    return JsonResponse(data, safe=False)


@require_http_methods(["GET"])
@authenticated
def recommendation_trends(request: HttpRequest) -> JsonResponse:
    period = request.GET.get("period", "day")
    days = {"day": 1, "week": 7, "month": 30}.get(period)
    if days is None:
        return JsonResponse({"detail": "Invalid trend period."}, status=400)
    since = timezone.now() - timedelta(days=days)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM run_candidate WHERE created_at >= %s",
            [since],
        )
        total = cursor.fetchone()[0]
        cursor.execute(
            """
            SELECT g.name, COUNT(*) AS recommendation_count
            FROM run_candidate rc
            JOIN content_genre cg ON cg.content_id = rc.content_id
            JOIN genre g ON g.id = cg.genre_id
            WHERE rc.created_at >= %s
            GROUP BY g.id, g.name
            ORDER BY recommendation_count DESC, g.name
            LIMIT 5
            """,
            [since],
        )
        genre_rows = cursor.fetchall()
        cursor.execute(
            """
            SELECT rc.content_id, COUNT(*) AS recommendation_count
            FROM run_candidate rc
            WHERE rc.created_at >= %s
            GROUP BY rc.content_id
            ORDER BY recommendation_count DESC, rc.content_id
            LIMIT 3
            """,
            [since],
        )
        content_trend_rows = cursor.fetchall()
    content_ids = [row[0] for row in content_trend_rows]
    content_by_id = {
        item["id"]: item
        for item in (
            fetch_content(
                "WHERE c.id = ANY(%s)",
                [content_ids],
            )
            if content_ids
            else []
        )
    }
    return JsonResponse(
        {
            "period": period,
            "totalRecommendations": total,
            "genreTrends": [
                {"genreName": row[0], "recommendationCount": row[1]}
                for row in genre_rows
            ],
            "contentTrends": [
                {
                    "content": content_by_id[str(content_id)],
                    "recommendationCount": count,
                }
                for content_id, count in content_trend_rows
                if str(content_id) in content_by_id
            ],
            "generatedAt": timezone.now().isoformat(),
        }
    )


@require_http_methods(["PATCH"])
@authenticated
def profile(request: HttpRequest) -> JsonResponse:
    data = request_data(request)
    if data is None:
        return JsonResponse({"detail": "Invalid JSON body."}, status=400)
    username = data.get("username")
    email = data.get("email")
    if not isinstance(username, str) or not isinstance(email, str):
        return JsonResponse({"detail": "Username and email are required."}, status=400)
    username = username.strip()
    email = email.strip().lower()
    if not username or not email:
        return JsonResponse({"detail": "Username and email are required."}, status=400)
    user_model = get_user_model()
    if user_model.objects.exclude(pk=request.user.pk).filter(
        username__iexact=username
    ).exists():
        return JsonResponse({"detail": "Username is already in use."}, status=409)
    if user_model.objects.exclude(pk=request.user.pk).filter(
        email__iexact=email
    ).exists():
        return JsonResponse({"detail": "Email is already in use."}, status=409)
    try:
        with transaction.atomic():
            request.user.username = username
            request.user.email = email
            request.user.full_clean(exclude=["password"])
            request.user.save(update_fields=["username", "email"])
            user = sync_business_user(request.user)
    except IntegrityError:
        return JsonResponse(
            {"detail": "Username or email is already in use."},
            status=409,
        )
    return JsonResponse({"user": user})


@require_http_methods(["GET", "POST"])
@authenticated
def conversations(request: HttpRequest) -> JsonResponse:
    user_id = get_business_user_id(request.user)
    if request.method == "GET":
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id, title, created_at, updated_at
                FROM conversation WHERE user_id = %s
                ORDER BY updated_at DESC, id DESC
                """,
                [user_id],
            )
            rows = cursor.fetchall()
        return JsonResponse([serialize_conversation(row) for row in rows], safe=False)
    now = timezone.now()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO conversation (user_id, title, created_at, updated_at)
            VALUES (%s, NULL, %s, %s)
            RETURNING id, user_id, title, created_at, updated_at
            """,
            [user_id, now, now],
        )
        row = cursor.fetchone()
    return JsonResponse(serialize_conversation(row), status=201)


@require_http_methods(["PATCH", "DELETE"])
@authenticated
def conversation_detail(request: HttpRequest, conversation_id: int) -> JsonResponse:
    user_id = get_business_user_id(request.user)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id FROM conversation WHERE id = %s AND user_id = %s",
            [conversation_id, user_id],
        )
        if cursor.fetchone() is None:
            return JsonResponse({"detail": "Conversation not found."}, status=404)
        if request.method == "DELETE":
            cursor.execute("DELETE FROM conversation WHERE id = %s", [conversation_id])
            return JsonResponse({}, status=204)
        data = request_data(request)
        title = data.get("title") if data else None
        if not isinstance(title, str) or not title.strip():
            return JsonResponse({"detail": "Title is required."}, status=400)
        cursor.execute(
            """
            UPDATE conversation
            SET title = %s, updated_at = %s
            WHERE id = %s
            RETURNING id, user_id, title, created_at, updated_at
            """,
            [title.strip()[:255], timezone.now(), conversation_id],
        )
        return JsonResponse(serialize_conversation(cursor.fetchone()))


@require_http_methods(["POST"])
@authenticated
def conversation_messages(
    request: HttpRequest,
    conversation_id: int,
) -> JsonResponse:
    user_id = get_business_user_id(request.user)
    data = request_data(request)
    content = data.get("content") if data else None
    if not isinstance(content, str) or not content.strip():
        return JsonResponse({"detail": "Message content is required."}, status=400)
    now = timezone.now()
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id FROM conversation
            WHERE id = %s AND user_id = %s
            FOR UPDATE
            """,
            [conversation_id, user_id],
        )
        if cursor.fetchone() is None:
            return JsonResponse({"detail": "Conversation not found."}, status=404)
        cursor.execute(
            "SELECT COALESCE(MAX(sequence_no), 0) + 1 FROM message WHERE conversation_id = %s",
            [conversation_id],
        )
        sequence_no = cursor.fetchone()[0]
        cursor.execute(
            """
            INSERT INTO message (
                conversation_id, role, content, sequence_no, created_at
            )
            VALUES (%s, 'user', %s, %s, %s)
            RETURNING id, conversation_id, role::text, content, sequence_no, created_at
            """,
            [conversation_id, content.strip(), sequence_no, now],
        )
        row = cursor.fetchone()
        cursor.execute(
            """
            UPDATE conversation
            SET title = COALESCE(title, %s), updated_at = %s
            WHERE id = %s
            """,
            [content.strip()[:255], now, conversation_id],
        )
    return JsonResponse(serialize_message(row), status=201)


@require_http_methods(["POST"])
@authenticated
def interactions(request: HttpRequest) -> JsonResponse:
    user_id = get_business_user_id(request.user)
    data = request_data(request)
    if data is None:
        return JsonResponse({"detail": "Invalid JSON body."}, status=400)
    try:
        content_id = int(data.get("content_id"))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "Valid content_id is required."}, status=400)
    source_candidate_id = data.get("source_candidate_id")
    try:
        source_candidate_id = (
            int(source_candidate_id) if source_candidate_id is not None else None
        )
    except (TypeError, ValueError):
        return JsonResponse({"detail": "Invalid source_candidate_id."}, status=400)
    interaction_type = data.get("interaction_type")
    allowed_types = {
        "details_opened",
        "liked",
        "disliked",
        "watchlisted",
        "watched",
        "rated",
    }
    if interaction_type not in allowed_types:
        return JsonResponse({"detail": "Invalid interaction_type."}, status=400)
    rating = data.get("rating")
    if interaction_type == "rated":
        if not isinstance(rating, (int, float)) or not 0 <= rating <= 10:
            return JsonResponse(
                {"detail": "Rated interaction requires rating from 0 to 10."},
                status=400,
            )
    else:
        rating = None
    with connection.cursor() as cursor:
        cursor.execute("SELECT EXISTS (SELECT 1 FROM content WHERE id = %s)", [content_id])
        if not cursor.fetchone()[0]:
            return JsonResponse({"detail": "Content not found."}, status=404)
        if interaction_type in {"watchlisted", "watched"}:
            cursor.execute(
                """
                SELECT id, user_id, content_id, source_candidate_id,
                       interaction_type::text, rating, metadata, created_at
                FROM interaction
                WHERE user_id = %s AND content_id = %s AND interaction_type = %s
                ORDER BY id DESC LIMIT 1
                """,
                [user_id, content_id, interaction_type],
            )
            existing = cursor.fetchone()
            if existing:
                return JsonResponse(serialize_interaction(existing))
        cursor.execute(
            """
            INSERT INTO interaction (
                user_id, content_id, source_candidate_id, interaction_type,
                rating, metadata, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, content_id, source_candidate_id,
                      interaction_type::text, rating, metadata, created_at
            """,
            [
                user_id,
                content_id,
                source_candidate_id,
                interaction_type,
                rating,
                Jsonb(data.get("metadata") if isinstance(data.get("metadata"), dict) else {}),
                timezone.now(),
            ],
        )
        row = cursor.fetchone()
    return JsonResponse(serialize_interaction(row), status=201)


@require_http_methods(["DELETE"])
@authenticated
def interaction_detail(request: HttpRequest, interaction_id: int) -> JsonResponse:
    user_id = get_business_user_id(request.user)
    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM interaction WHERE id = %s AND user_id = %s RETURNING id",
            [interaction_id, user_id],
        )
        if cursor.fetchone() is None:
            return JsonResponse({"detail": "Interaction not found."}, status=404)
    return JsonResponse({}, status=204)
