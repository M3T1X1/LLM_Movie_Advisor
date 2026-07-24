import json
import logging
import os
from datetime import date, timedelta
from functools import wraps
from math import ceil

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import CommandError
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.db.models import Count, F, Max, Prefetch, Q
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from backend.accounts.management.commands.seed_demo_data import (
    Command as SeedDemoCommand,
)
from backend.accounts.management.commands.seed_demo_data import (
    TmdbClient,
    normalize_tmdb_item,
)
from backend.accounts.services import get_business_user_id, sync_business_user
from backend.api.models import (
    BusinessUser,
    Content,
    Conversation,
    Genre,
    Interaction,
    InteractionType,
    Message,
    MessageRole,
    RunCandidate,
    UserPreference,
    UserProfile,
)


logger = logging.getLogger(__name__)
MAX_CHAT_MESSAGE_LENGTH = 800
CATALOG_DEFAULT_PAGE_SIZE = 20
CATALOG_MAX_PAGE_SIZE = 50
CATALOG_SORTS = {
    "popularity": (F("popularity").desc(nulls_last=True), "id"),
    "rating": (F("vote_average").desc(nulls_last=True), "id"),
    "newest": (F("release_date").desc(nulls_last=True), "id"),
    "title": ("title", "id"),
}


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


def content_queryset():
    return Content.objects.prefetch_related(
        Prefetch("genres", queryset=Genre.objects.order_by("name"))
    )


def serialize_content(item: Content) -> dict:
    return {
        "id": str(item.pk),
        "tmdbId": item.tmdb_id,
        "mediaType": item.media_type,
        "title": item.title,
        "originalTitle": item.original_title,
        "overview": item.overview,
        "releaseDate": iso(item.release_date),
        "originalLanguage": item.original_language,
        "posterPath": item.poster_path,
        "voteAverage": (
            float(item.vote_average) if item.vote_average is not None else None
        ),
        "popularity": float(item.popularity) if item.popularity is not None else None,
        "metadata": json_object(item.metadata),
        "tmdbRefreshedAt": iso(item.tmdb_refreshed_at),
        "genres": [
            {
                "id": str(genre.pk),
                "tmdbGenreId": genre.tmdb_genre_id,
                "name": genre.name,
            }
            for genre in item.genres.all()
        ],
    }


def serialize_conversation(item: Conversation) -> dict:
    return {
        "id": str(item.pk),
        "userId": str(item.user_id),
        "title": item.title,
        "createdAt": iso(item.created_at),
        "updatedAt": iso(item.updated_at),
    }


def serialize_message(item: Message) -> dict:
    return {
        "id": str(item.pk),
        "conversationId": str(item.conversation_id),
        "role": item.role,
        "content": item.content,
        "sequenceNo": item.sequence_no,
        "createdAt": iso(item.created_at),
    }


def serialize_interaction(item: Interaction) -> dict:
    return {
        "id": str(item.pk),
        "userId": str(item.user_id),
        "contentId": str(item.content_id),
        "sourceCandidateId": (
            str(item.source_candidate_id)
            if item.source_candidate_id is not None
            else None
        ),
        "interactionType": item.interaction_type,
        "rating": float(item.rating) if item.rating is not None else None,
        "metadata": json_object(item.metadata),
        "createdAt": iso(item.created_at),
    }


@require_http_methods(["GET"])
def health(request: HttpRequest) -> JsonResponse:
    try:
        connection.ensure_connection()
    except DatabaseError:
        logger.exception("Database health check failed.")
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


@require_http_methods(["GET"])
@authenticated
def bootstrap(request: HttpRequest) -> JsonResponse:
    user_id = get_business_user_id(request.user)
    user = sync_business_user(request.user)
    profile = UserProfile.objects.filter(user_id=user_id).first()
    preferences = UserPreference.objects.filter(user_id=user_id).order_by(
        "-polarity", "-weight", "id"
    )
    conversations = list(
        Conversation.objects.filter(user_id=user_id).order_by("-updated_at", "-id")
    )
    messages = Message.objects.filter(
        conversation_id__in=[item.pk for item in conversations]
    ).order_by("conversation_id", "sequence_no")
    interactions = Interaction.objects.filter(user_id=user_id).order_by(
        "created_at", "id"
    )

    profile_data = {
        "userId": str(user_id),
        "semanticSummary": profile.semantic_summary if profile else None,
        "version": profile.version if profile else 1,
        "lastRebuiltAt": iso(profile.last_rebuilt_at) if profile else None,
        "updatedAt": iso(profile.updated_at) if profile else iso(timezone.now()),
    }
    preference_data = [
        {
            "id": str(item.pk),
            "userId": str(item.user_id),
            "preferenceType": item.preference_type,
            "preferenceValue": item.preference_value,
            "polarity": item.polarity,
            "weight": float(item.weight),
            "confidence": float(item.confidence),
            "createdAt": iso(item.created_at),
            "updatedAt": iso(item.updated_at),
        }
        for item in preferences
    ]
    return JsonResponse(
        {
            "user": user,
            "semanticProfile": profile_data,
            "preferences": preference_data,
            "conversations": [serialize_conversation(item) for item in conversations],
            "messages": [serialize_message(item) for item in messages],
            "interactions": [serialize_interaction(item) for item in interactions],
        }
    )


@require_http_methods(["GET"])
@authenticated
def contents(request: HttpRequest) -> JsonResponse:
    try:
        page = int(request.GET.get("page", "1"))
        page_size = int(
            request.GET.get("page_size", str(CATALOG_DEFAULT_PAGE_SIZE))
        )
    except ValueError:
        return JsonResponse(
            {"detail": "Page and page_size must be integers."},
            status=400,
        )
    if page < 1:
        return JsonResponse({"detail": "Page must be at least 1."}, status=400)
    if not 1 <= page_size <= CATALOG_MAX_PAGE_SIZE:
        return JsonResponse(
            {
                "detail": (
                    f"Page size must be between 1 and "
                    f"{CATALOG_MAX_PAGE_SIZE}."
                )
            },
            status=400,
        )

    query = request.GET.get("q", "").strip()
    media_type = request.GET.get("media_type", "all")
    genre = request.GET.get("genre", "").strip()
    sort = request.GET.get("sort", "popularity")
    if len(query) > 200:
        return JsonResponse(
            {"detail": "Search query cannot exceed 200 characters."},
            status=400,
        )
    if len(genre) > 100:
        return JsonResponse(
            {"detail": "Genre cannot exceed 100 characters."},
            status=400,
        )
    if media_type not in {"all", "movie", "tv"}:
        return JsonResponse({"detail": "Invalid media_type."}, status=400)
    if sort not in CATALOG_SORTS:
        return JsonResponse({"detail": "Invalid sort option."}, status=400)

    queryset = content_queryset()
    ids_value = request.GET.get("ids", "").strip()
    if ids_value:
        try:
            content_ids = [
                int(value)
                for value in ids_value.split(",")
                if value.strip()
            ]
        except ValueError:
            return JsonResponse(
                {"detail": "ids must be comma-separated integers."},
                status=400,
            )
        if (
            not content_ids
            or len(content_ids) > CATALOG_MAX_PAGE_SIZE
            or any(content_id < 1 for content_id in content_ids)
        ):
            return JsonResponse(
                {
                    "detail": (
                        f"ids must contain between 1 and "
                        f"{CATALOG_MAX_PAGE_SIZE} positive identifiers."
                    )
                },
                status=400,
            )
        queryset = queryset.filter(pk__in=list(dict.fromkeys(content_ids)))
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query) | Q(original_title__icontains=query)
        )
    if media_type != "all":
        queryset = queryset.filter(media_type=media_type)
    if genre:
        queryset = queryset.filter(genres__name__iexact=genre)

    minimum_rating_value = request.GET.get("min_rating")
    if minimum_rating_value not in {None, ""}:
        try:
            minimum_rating = float(minimum_rating_value)
        except ValueError:
            return JsonResponse(
                {"detail": "min_rating must be a number."},
                status=400,
            )
        if not 0 <= minimum_rating <= 10:
            return JsonResponse(
                {"detail": "min_rating must be between 0 and 10."},
                status=400,
            )
        queryset = queryset.filter(vote_average__gte=minimum_rating)

    year_from_value = request.GET.get("year_from")
    if year_from_value not in {None, ""}:
        try:
            year_from = int(year_from_value)
        except ValueError:
            return JsonResponse(
                {"detail": "year_from must be an integer."},
                status=400,
            )
        if not 1888 <= year_from <= date.today().year + 10:
            return JsonResponse(
                {"detail": "year_from is outside the supported range."},
                status=400,
            )
        queryset = queryset.filter(release_date__gte=date(year_from, 1, 1))

    queryset = queryset.distinct()
    total_items = queryset.count()
    genres = list(
        Genre.objects.filter(contents__isnull=False)
        .order_by("name")
        .values_list("name", flat=True)
        .distinct()
    )

    total_pages = ceil(total_items / page_size) if total_items else 0
    start = (page - 1) * page_size
    items = list(
        queryset.order_by(*CATALOG_SORTS[sort])[start : start + page_size]
    )
    return JsonResponse(
        {
            "items": [serialize_content(item) for item in items],
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "totalItems": total_items,
                "totalPages": total_pages,
                "hasPrevious": page > 1,
                "hasNext": page < total_pages,
            },
            "filters": {"genres": genres},
        }
    )


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
    has_fresh_data = Content.objects.filter(
        media_type="movie",
        release_date__gte=date.today(),
        tmdb_refreshed_at__gte=timezone.now() - timedelta(hours=12),
    ).exists()
    if refresh or not has_fresh_data:
        try:
            sync_upcoming_from_tmdb()
        except CommandError as error:
            logger.warning("TMDB upcoming synchronization failed: %s", error)
            if refresh:
                return JsonResponse(
                    {"detail": "TMDB upcoming releases are unavailable."},
                    status=503,
                )
    data = content_queryset().filter(
        media_type="movie",
        release_date__gte=date.today(),
    ).order_by(
        "release_date",
        F("popularity").desc(nulls_last=True),
    )
    return JsonResponse([serialize_content(item) for item in data], safe=False)


@require_http_methods(["GET"])
@authenticated
def recommendation_trends(request: HttpRequest) -> JsonResponse:
    period = request.GET.get("period", "day")
    days = {"day": 1, "week": 7, "month": 30}.get(period)
    if days is None:
        return JsonResponse({"detail": "Invalid trend period."}, status=400)
    since = timezone.now() - timedelta(days=days)
    candidates = RunCandidate.objects.filter(created_at__gte=since)
    total = candidates.count()
    genre_rows = list(
        Genre.objects.filter(contents__run_candidates__created_at__gte=since)
        .values("name")
        .annotate(recommendation_count=Count("contents__run_candidates"))
        .order_by("-recommendation_count", "name")[:5]
    )
    content_trend_rows = list(
        candidates.values("content_id")
        .annotate(recommendation_count=Count("id"))
        .order_by("-recommendation_count", "content_id")[:3]
    )
    content_by_id = {
        item.pk: item
        for item in content_queryset().filter(
            pk__in=[row["content_id"] for row in content_trend_rows]
        )
    }
    return JsonResponse(
        {
            "period": period,
            "totalRecommendations": total,
            "genreTrends": [
                {
                    "genreName": row["name"],
                    "recommendationCount": row["recommendation_count"],
                }
                for row in genre_rows
            ],
            "contentTrends": [
                {
                    "content": serialize_content(
                        content_by_id[row["content_id"]]
                    ),
                    "recommendationCount": row["recommendation_count"],
                }
                for row in content_trend_rows
                if row["content_id"] in content_by_id
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
    business_user_id = get_business_user_id(request.user)
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
            user = sync_business_user(
                request.user,
                business_user_id=business_user_id,
            )
    except ValidationError as error:
        return JsonResponse({"detail": " ".join(error.messages)}, status=400)
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
        items = Conversation.objects.filter(user_id=user_id).order_by(
            "-updated_at", "-id"
        )
        return JsonResponse(
            [serialize_conversation(item) for item in items],
            safe=False,
        )
    item = Conversation.objects.create(user_id=user_id)
    return JsonResponse(serialize_conversation(item), status=201)


@require_http_methods(["PATCH", "DELETE"])
@authenticated
def conversation_detail(request: HttpRequest, conversation_id: int) -> JsonResponse:
    user_id = get_business_user_id(request.user)
    item = Conversation.objects.filter(
        pk=conversation_id,
        user_id=user_id,
    ).first()
    if item is None:
        return JsonResponse({"detail": "Conversation not found."}, status=404)
    if request.method == "DELETE":
        item.delete()
        return JsonResponse({}, status=204)
    data = request_data(request)
    title = data.get("title") if data else None
    if not isinstance(title, str) or not title.strip():
        return JsonResponse({"detail": "Title is required."}, status=400)
    item.title = title.strip()[:255]
    item.updated_at = timezone.now()
    item.save(update_fields=["title", "updated_at"])
    return JsonResponse(serialize_conversation(item))


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
    if len(content.strip()) > MAX_CHAT_MESSAGE_LENGTH:
        return JsonResponse(
            {
                "detail": (
                    f"Message content cannot exceed "
                    f"{MAX_CHAT_MESSAGE_LENGTH} characters."
                )
            },
            status=400,
        )
    with transaction.atomic():
        conversation = (
            Conversation.objects.select_for_update()
            .filter(pk=conversation_id, user_id=user_id)
            .first()
        )
        if conversation is None:
            return JsonResponse({"detail": "Conversation not found."}, status=404)
        maximum = Message.objects.filter(conversation=conversation).aggregate(
            maximum=Max("sequence_no")
        )["maximum"]
        message = Message.objects.create(
            conversation=conversation,
            role=MessageRole.USER,
            content=content.strip(),
            sequence_no=(maximum or 0) + 1,
        )
        if conversation.title is None:
            conversation.title = content.strip()[:255]
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=["title", "updated_at"])
    return JsonResponse(serialize_message(message), status=201)


@require_http_methods(["POST"])
@authenticated
def interactions(request: HttpRequest) -> JsonResponse:
    user_id = get_business_user_id(request.user)
    data = request_data(request)
    if data is None:
        return JsonResponse({"detail": "Invalid JSON body."}, status=400)
    try:
        raw_content_id = data.get("content_id")
        if isinstance(raw_content_id, bool):
            raise ValueError
        content_id = int(raw_content_id)
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
        if (
            isinstance(rating, bool)
            or not isinstance(rating, (int, float))
            or not 0 <= rating <= 10
        ):
            return JsonResponse(
                {"detail": "Rated interaction requires rating from 0 to 10."},
                status=400,
            )
    else:
        rating = None
    if not Content.objects.filter(pk=content_id).exists():
        return JsonResponse({"detail": "Content not found."}, status=404)
    if source_candidate_id is not None:
        source_candidate_exists = RunCandidate.objects.filter(
            pk=source_candidate_id,
            content_id=content_id,
            run__request__conversation__user_id=user_id,
        ).exists()
        if not source_candidate_exists:
            return JsonResponse(
                {"detail": "Source candidate not found."},
                status=404,
            )
    if interaction_type in {
        InteractionType.WATCHLISTED,
        InteractionType.WATCHED,
    }:
        existing = (
            Interaction.objects.filter(
                user_id=user_id,
                content_id=content_id,
                interaction_type=interaction_type,
            )
            .order_by("-id")
            .first()
        )
        if existing:
            return JsonResponse(serialize_interaction(existing))
    item = Interaction.objects.create(
        user_id=user_id,
        content_id=content_id,
        source_candidate_id=source_candidate_id,
        interaction_type=interaction_type,
        rating=rating,
        metadata=data.get("metadata")
        if isinstance(data.get("metadata"), dict)
        else {},
    )
    return JsonResponse(serialize_interaction(item), status=201)


@require_http_methods(["DELETE"])
@authenticated
def interaction_detail(request: HttpRequest, interaction_id: int) -> JsonResponse:
    user_id = get_business_user_id(request.user)
    deleted, _ = Interaction.objects.filter(
        pk=interaction_id,
        user_id=user_id,
    ).delete()
    if not deleted:
        return JsonResponse({"detail": "Interaction not found."}, status=404)
    return JsonResponse({}, status=204)
