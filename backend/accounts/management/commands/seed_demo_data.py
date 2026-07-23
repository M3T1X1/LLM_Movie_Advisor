import json
import os
import random
import time
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone
from psycopg.types.json import Jsonb


TMDB_API_URL = "https://api.themoviedb.org/3"
TMDB_PAGE_SIZE = 20
TMDB_MAX_PAGES = 500
REQUIRED_TABLES = {
    "agent_execution",
    "app_user",
    "content",
    "content_genre",
    "conversation",
    "genre",
    "interaction",
    "message",
    "recommendation_request",
    "recommendation_run",
    "run_candidate",
    "user_preference",
    "user_profile",
}

DEMO_USERS = (
    {
        "username": "kacper",
        "email": "kacper@example.com",
        "summary": (
            "Preferuje mroczne thrillery, ambitne science fiction, powolne budowanie "
            "napięcia i niejednoznaczne zakończenia."
        ),
        "preferences": (
            ("genre", "Thriller", 1, 0.96, 0.95),
            ("genre", "Science Fiction", 1, 0.91, 0.88),
            ("genre", "Dramat", 1, 0.82, 0.83),
            ("narrative", "Niejednoznaczne zakończenia", 1, 0.90, 0.91),
            ("pacing", "Powolne budowanie napięcia", 1, 0.86, 0.87),
            ("humor", "Slapstick", -1, 0.78, 0.84),
        ),
    },
    {
        "username": "ania",
        "email": "ania@example.com",
        "summary": (
            "Najchętniej ogląda kameralne dramaty, historie obyczajowe i kino "
            "z wyrazistymi bohaterkami; unika brutalnego horroru."
        ),
        "preferences": (
            ("genre", "Dramat", 1, 0.95, 0.94),
            ("genre", "Romans", 1, 0.82, 0.80),
            ("theme", "Relacje rodzinne", 1, 0.91, 0.88),
            ("character", "Silne bohaterki", 1, 0.88, 0.86),
            ("violence", "Nadmierny gore", -1, 0.93, 0.95),
            ("pacing", "Chaotyczna narracja", -1, 0.67, 0.72),
        ),
    },
    {
        "username": "marek",
        "email": "marek@example.com",
        "summary": (
            "Lubi dynamiczne kino akcji, kryminały i przygodowe widowiska, "
            "szczególnie z szybkim tempem i wyrazistym konfliktem."
        ),
        "preferences": (
            ("genre", "Akcja", 1, 0.97, 0.95),
            ("genre", "Kryminał", 1, 0.89, 0.87),
            ("genre", "Przygodowy", 1, 0.86, 0.84),
            ("pacing", "Szybkie tempo", 1, 0.94, 0.92),
            ("theme", "Napad i pościg", 1, 0.83, 0.81),
            ("narrative", "Bardzo wolne kino", -1, 0.72, 0.76),
        ),
    },
    {
        "username": "ola",
        "email": "ola@example.com",
        "summary": (
            "Wybiera lekkie komedie, animacje i krótkie seriale poprawiające "
            "nastrój; nie przepada za ponurymi, fatalistycznymi historiami."
        ),
        "preferences": (
            ("genre", "Komedia", 1, 0.96, 0.94),
            ("genre", "Animacja", 1, 0.89, 0.87),
            ("format", "Krótkie odcinki", 1, 0.87, 0.85),
            ("mood", "Podnoszący na duchu", 1, 0.93, 0.91),
            ("theme", "Przyjaźń", 1, 0.83, 0.82),
            ("mood", "Fatalistyczny", -1, 0.79, 0.82),
        ),
    },
    {
        "username": "piotr",
        "email": "piotr@example.com",
        "summary": (
            "Poszukuje dokumentów, historii opartych na faktach i wymagającego "
            "kina historycznego, z ograniczoną ilością schematycznego humoru."
        ),
        "preferences": (
            ("genre", "Dokumentalny", 1, 0.96, 0.95),
            ("genre", "Historyczny", 1, 0.88, 0.86),
            ("theme", "Oparte na faktach", 1, 0.94, 0.92),
            ("narrative", "Wielowątkowa opowieść", 1, 0.79, 0.77),
            ("pacing", "Spokojne tempo", 1, 0.75, 0.78),
            ("humor", "Schematyczne żarty", -1, 0.71, 0.75),
        ),
    },
)

CONVERSATION_SCENARIOS = (
    {
        "title": "Mroczny thriller z twistem",
        "prompt": "Szukam mrocznego thrillera z mocnym twistem i bez happy endu.",
        "mood": "mroczny",
        "context": {"themes": ["twist fabularny", "moralna niejednoznaczność"]},
        "constraints": {"ending": "bez happy endu"},
    },
    {
        "title": "Inteligentne science fiction",
        "prompt": "Poleć inteligentne science fiction, które daje do myślenia.",
        "mood": "refleksyjny",
        "context": {"themes": ["technologia", "tożsamość", "przyszłość"]},
        "constraints": {"minimum_vote_average": 7},
    },
    {
        "title": "Lekki serial na dwa wieczory",
        "prompt": "Chcę lekki serial z krótkimi odcinkami na dwa wieczory.",
        "mood": "lekki",
        "context": {"format": "serial", "pacing": "dynamiczne"},
        "constraints": {"episode_runtime_max": 45},
    },
    {
        "title": "Kino na wspólny wieczór",
        "prompt": "Znajdź angażujący film na wspólny wieczór, bez nadmiernej przemocy.",
        "mood": "towarzyski",
        "context": {"audience": "dwie osoby", "tone": "angażujący"},
        "constraints": {"avoid": ["gore", "skrajna przemoc"]},
    },
    {
        "title": "Historia oparta na faktach",
        "prompt": "Mam ochotę na dobrze ocenioną historię opartą na faktach.",
        "mood": "ciekawy",
        "context": {"themes": ["historia", "prawdziwe wydarzenia"]},
        "constraints": {"minimum_vote_average": 7.2},
    },
)

ASSISTANT_GREETING = (
    "Cześć! Opisz nastrój, tempo albo motyw, a przygotuję dopasowane propozycje."
)
ASSISTANT_RESPONSE = (
    "Przeanalizowałem Twój profil i bieżący kontekst. Wybrałem trzy tytuły, "
    "które najlepiej łączą wskazany klimat, tempo oraz Twoje długoterminowe preferencje."
)
AGENTS = (
    ("profiling", "Analiza profilu, nastroju i ograniczeń"),
    ("retrieval", "Pozyskanie i filtrowanie kandydatów z katalogu TMDB"),
    ("ranking", "Ocena zgodności kandydatów z profilem"),
    ("explanation", "Przygotowanie uzasadnień rekomendacji"),
)


@dataclass(frozen=True)
class TmdbCatalogItem:
    tmdb_id: int
    media_type: str
    title: str
    original_title: str | None
    overview: str | None
    release_date: date | None
    original_language: str | None
    poster_path: str | None
    vote_average: float | None
    popularity: float | None
    genre_ids: tuple[int, ...]
    metadata: dict[str, Any]


class TmdbClient:
    def __init__(
        self,
        *,
        api_key: str | None,
        access_token: str | None,
        timeout: float = 20,
        retries: int = 3,
    ):
        self.api_key = api_key
        self.access_token = access_token
        self.timeout = timeout
        self.retries = retries
        if not self.api_key and not self.access_token:
            raise CommandError(
                "TMDB credentials are required. Set TMDB_API_KEY or TMDB_API_TOKEN."
            )

    def get(self, path: str, **params: Any) -> dict[str, Any]:
        query = {key: value for key, value in params.items() if value is not None}
        if self.api_key:
            query["api_key"] = self.api_key
        url = f"{TMDB_API_URL}{path}?{urlencode(query)}"
        headers = {"Accept": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        for attempt in range(1, self.retries + 1):
            try:
                with urlopen(
                    Request(url, headers=headers),
                    timeout=self.timeout,
                ) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise CommandError(f"TMDB returned an invalid response for {path}.")
                return payload
            except HTTPError as error:
                if error.code in {429, 500, 502, 503, 504} and attempt < self.retries:
                    time.sleep(attempt)
                    continue
                detail = error.read().decode("utf-8", errors="replace")[:300]
                raise CommandError(
                    f"TMDB request failed ({error.code}) for {path}: {detail}"
                ) from error
            except (URLError, TimeoutError, json.JSONDecodeError) as error:
                if attempt < self.retries:
                    time.sleep(attempt)
                    continue
                raise CommandError(f"TMDB request failed for {path}: {error}") from error

        raise CommandError(f"TMDB request failed for {path}.")

    def fetch_genres(self) -> dict[int, str]:
        genres: dict[int, str] = {}
        for path in ("/genre/movie/list", "/genre/tv/list"):
            payload = self.get(path, language="pl-PL")
            for genre in payload.get("genres", []):
                if isinstance(genre, dict) and isinstance(genre.get("id"), int):
                    genres[genre["id"]] = str(genre.get("name") or genre["id"])
        if not genres:
            raise CommandError("TMDB returned no genres.")
        return genres

    def fetch_catalog(self, *, movies: int, tv_shows: int) -> list[TmdbCatalogItem]:
        catalog: list[TmdbCatalogItem] = []
        catalog.extend(self._fetch_popular("movie", movies))
        catalog.extend(self._fetch_popular("tv", tv_shows))
        return catalog

    def _fetch_popular(self, media_type: str, target_count: int) -> list[TmdbCatalogItem]:
        if target_count <= 0:
            return []

        items: list[TmdbCatalogItem] = []
        seen_ids: set[int] = set()
        page = 1
        available_pages = TMDB_MAX_PAGES
        pages_checked = 0
        pages_without_new_items = 0
        while len(items) < target_count and page <= available_pages:
            payload = self.get(
                f"/{media_type}/popular",
                language="pl-PL",
                page=page,
                region="PL" if media_type == "movie" else None,
            )
            pages_checked += 1
            results = payload.get("results")
            if not isinstance(results, list):
                raise CommandError(
                    f"TMDB returned an invalid popular {media_type} response."
                )
            reported_total_pages = payload.get("total_pages")
            if (
                isinstance(reported_total_pages, int)
                and not isinstance(reported_total_pages, bool)
                and reported_total_pages > 0
            ):
                available_pages = min(reported_total_pages, TMDB_MAX_PAGES)

            item_count_before_page = len(items)
            for raw_item in results:
                item = normalize_tmdb_item(raw_item, media_type)
                if item is None or item.tmdb_id in seen_ids:
                    continue
                items.append(item)
                seen_ids.add(item.tmdb_id)
                if len(items) >= target_count:
                    return items

            if not results:
                break
            if len(items) == item_count_before_page:
                pages_without_new_items += 1
                if pages_without_new_items >= 3:
                    break
            else:
                pages_without_new_items = 0
            page += 1

        if len(items) < target_count:
            raise CommandError(
                f"TMDB returned only {len(items)} unique {media_type} items; "
                f"{target_count} requested after checking {pages_checked} page(s)."
            )
        return items


def normalize_tmdb_item(
    raw_item: Any,
    media_type: str,
) -> TmdbCatalogItem | None:
    if not isinstance(raw_item, dict) or media_type not in {"movie", "tv"}:
        return None
    tmdb_id = raw_item.get("id")
    title_key = "title" if media_type == "movie" else "name"
    original_title_key = "original_title" if media_type == "movie" else "original_name"
    date_key = "release_date" if media_type == "movie" else "first_air_date"
    title = raw_item.get(title_key)
    if not isinstance(tmdb_id, int) or not isinstance(title, str) or not title.strip():
        return None

    raw_genre_ids = raw_item.get("genre_ids")
    if not isinstance(raw_genre_ids, list):
        raw_genre_ids = []
    genre_ids = tuple(
        genre_id
        for genre_id in raw_genre_ids
        if isinstance(genre_id, int)
    )
    metadata = {
        "voteCount": positive_int_or_none(raw_item.get("vote_count")),
        "backdropPath": nullable_string(raw_item.get("backdrop_path")),
        "adult": bool(raw_item.get("adult", False)),
        "originCountry": [
            country
            for country in raw_item.get("origin_country", [])
            if isinstance(country, str)
        ],
        "source": "tmdb",
    }
    return TmdbCatalogItem(
        tmdb_id=tmdb_id,
        media_type=media_type,
        title=title.strip()[:500],
        original_title=nullable_string(raw_item.get(original_title_key), limit=500),
        overview=nullable_string(raw_item.get("overview")),
        release_date=parse_date(raw_item.get(date_key)),
        original_language=nullable_string(raw_item.get("original_language"), limit=20),
        poster_path=nullable_string(raw_item.get("poster_path"), limit=500),
        vote_average=bounded_float(raw_item.get("vote_average"), 0, 10),
        popularity=bounded_float(raw_item.get("popularity"), 0, None),
        genre_ids=genre_ids,
        metadata=metadata,
    )


def nullable_string(value: Any, *, limit: int | None = None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized[:limit] if limit else normalized


def parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def bounded_float(value: Any, minimum: float, maximum: float | None) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    result = float(value)
    if result < minimum or (maximum is not None and result > maximum):
        return None
    return result


def positive_int_or_none(value: Any) -> int | None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return None
    return value


class Command(BaseCommand):
    help = (
        "Seeds the full development database and synchronizes movie/TV metadata "
        "from TMDB."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--movies",
            type=int,
            default=1500,
            help="Number of popular movies fetched from TMDB (default: 1500).",
        )
        parser.add_argument(
            "--tv-shows",
            type=int,
            default=1500,
            help="Number of popular TV shows fetched from TMDB (default: 1500).",
        )
        parser.add_argument(
            "--users",
            type=int,
            default=5,
            help="Number of demo users, from 1 to 5 (default: 5).",
        )
        parser.add_argument(
            "--password",
            default=os.environ.get("SEED_USER_PASSWORD"),
            help="Shared demo password. Prefer setting SEED_USER_PASSWORD.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo data can only be loaded when DEBUG=True.")

        movies = options["movies"]
        tv_shows = options["tv_shows"]
        user_count = options["users"]
        password = options["password"]
        if not 1 <= user_count <= len(DEMO_USERS):
            raise CommandError(f"--users must be between 1 and {len(DEMO_USERS)}.")
        if movies < 3 or tv_shows < 0:
            raise CommandError("--movies must be at least 3 and --tv-shows cannot be negative.")
        if movies + tv_shows < 3:
            raise CommandError("At least 3 catalog items are required.")
        if not password:
            raise CommandError(
                "Password is required. Use --password or SEED_USER_PASSWORD."
            )
        try:
            validate_password(password)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error

        self._check_schema()
        client = TmdbClient(
            api_key=os.environ.get("TMDB_API_KEY"),
            access_token=os.environ.get("TMDB_API_TOKEN"),
        )
        self.stdout.write(
            f"Fetching {movies} movies, {tv_shows} TV shows and genres from TMDB..."
        )
        genres = client.fetch_genres()
        catalog = client.fetch_catalog(movies=movies, tv_shows=tv_shows)

        with transaction.atomic():
            business_user_ids = self._seed_users(password, user_count)
            content_ids = self._seed_catalog(genres, catalog)
            conversation_ids, candidates = self._seed_recommendation_history(
                business_user_ids,
                content_ids,
            )
            self._seed_interactions(
                business_user_ids,
                content_ids,
                candidates,
            )

        counts = self._seeded_counts()
        self.stdout.write(self.style.SUCCESS("Full demo database seeded successfully."))
        self.stdout.write(
            "Seeded totals: "
            + ", ".join(f"{table}={count}" for table, count in counts.items())
        )
        self.stdout.write(
            f"Demo users: {', '.join(user['email'] for user in DEMO_USERS[:user_count])}"
        )
        self.stdout.write(
            f"Conversations prepared: {len(conversation_ids)}; "
            f"embeddings intentionally skipped."
        )

    def _check_schema(self):
        table_names = set(connection.introspection.table_names())
        missing = sorted(REQUIRED_TABLES - table_names)
        if missing:
            raise CommandError(
                "Business database tables are missing: "
                f"{', '.join(missing)}. Apply the PostgreSQL schema first."
            )

    def _seed_users(self, password: str, user_count: int) -> list[int]:
        user_model = get_user_model()
        business_ids: list[int] = []
        now = timezone.now()

        for definition in DEMO_USERS[:user_count]:
            auth_user = user_model.objects.filter(username=definition["username"]).first()
            if auth_user is None:
                auth_user = user_model(username=definition["username"])
            auth_user.email = definition["email"]
            auth_user.is_active = True
            auth_user.set_password(password)
            auth_user.full_clean()
            auth_user.save()

            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id
                    FROM app_user
                    WHERE username = %s OR email = %s
                    ORDER BY (username = %s) DESC
                    LIMIT 1
                    """,
                    [
                        definition["username"],
                        definition["email"],
                        definition["username"],
                    ],
                )
                row = cursor.fetchone()
                if row:
                    business_user_id = row[0]
                    cursor.execute(
                        """
                        UPDATE app_user
                        SET email = %s, username = %s, password = %s, is_active = TRUE
                        WHERE id = %s
                        """,
                        [
                            definition["email"],
                            definition["username"],
                            auth_user.password,
                            business_user_id,
                        ],
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO app_user (email, username, password, date_joined, is_active)
                        VALUES (%s, %s, %s, %s, TRUE)
                        RETURNING id
                        """,
                        [
                            definition["email"],
                            definition["username"],
                            auth_user.password,
                            now,
                        ],
                    )
                    business_user_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO user_profile (
                        user_id, semantic_summary, version, last_rebuilt_at, updated_at
                    )
                    VALUES (%s, %s, 1, %s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET
                        semantic_summary = EXCLUDED.semantic_summary,
                        version = EXCLUDED.version,
                        last_rebuilt_at = EXCLUDED.last_rebuilt_at,
                        updated_at = EXCLUDED.updated_at
                    """,
                    [business_user_id, definition["summary"], now, now],
                )
                for (
                    preference_type,
                    preference_value,
                    polarity,
                    weight,
                    confidence,
                ) in definition["preferences"]:
                    cursor.execute(
                        """
                        INSERT INTO user_preference (
                            user_id, preference_type, preference_value, polarity,
                            weight, confidence, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, preference_type, preference_value)
                        DO UPDATE SET
                            polarity = EXCLUDED.polarity,
                            weight = EXCLUDED.weight,
                            confidence = EXCLUDED.confidence,
                            updated_at = EXCLUDED.updated_at
                        """,
                        [
                            business_user_id,
                            preference_type,
                            preference_value,
                            polarity,
                            weight,
                            confidence,
                            now,
                            now,
                        ],
                    )
            business_ids.append(business_user_id)
        return business_ids

    def _seed_catalog(
        self,
        genres: dict[int, str],
        catalog: list[TmdbCatalogItem],
    ) -> list[int]:
        now = timezone.now()
        genre_database_ids: dict[int, int] = {}
        content_ids: list[int] = []
        with connection.cursor() as cursor:
            for tmdb_genre_id, name in sorted(genres.items()):
                cursor.execute(
                    """
                    INSERT INTO genre (tmdb_genre_id, name)
                    VALUES (%s, %s)
                    ON CONFLICT (tmdb_genre_id) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """,
                    [tmdb_genre_id, name[:100]],
                )
                genre_database_ids[tmdb_genre_id] = cursor.fetchone()[0]

            for item in catalog:
                cursor.execute(
                    """
                    INSERT INTO content (
                        tmdb_id, media_type, title, original_title, overview,
                        release_date, original_language, poster_path, vote_average,
                        popularity, metadata, tmdb_refreshed_at
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (tmdb_id, media_type) DO UPDATE SET
                        title = EXCLUDED.title,
                        original_title = EXCLUDED.original_title,
                        overview = EXCLUDED.overview,
                        release_date = EXCLUDED.release_date,
                        original_language = EXCLUDED.original_language,
                        poster_path = EXCLUDED.poster_path,
                        vote_average = EXCLUDED.vote_average,
                        popularity = EXCLUDED.popularity,
                        metadata = EXCLUDED.metadata,
                        tmdb_refreshed_at = EXCLUDED.tmdb_refreshed_at
                    RETURNING id
                    """,
                    [
                        item.tmdb_id,
                        item.media_type,
                        item.title,
                        item.original_title,
                        item.overview,
                        item.release_date,
                        item.original_language,
                        item.poster_path,
                        item.vote_average,
                        item.popularity,
                        Jsonb(item.metadata),
                        now,
                    ],
                )
                content_id = cursor.fetchone()[0]
                content_ids.append(content_id)
                cursor.execute(
                    "DELETE FROM content_genre WHERE content_id = %s",
                    [content_id],
                )
                for tmdb_genre_id in item.genre_ids:
                    genre_id = genre_database_ids.get(tmdb_genre_id)
                    if genre_id is None:
                        continue
                    cursor.execute(
                        """
                        INSERT INTO content_genre (content_id, genre_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        [content_id, genre_id],
                    )
        return content_ids

    def _seed_recommendation_history(
        self,
        user_ids: list[int],
        content_ids: list[int],
    ) -> tuple[list[int], list[tuple[int, int]]]:
        now = timezone.now()
        conversation_ids: list[int] = []
        candidates: list[tuple[int, int]] = []
        history_index = 0

        for user_index, user_id in enumerate(user_ids):
            for scenario_index, scenario in enumerate(CONVERSATION_SCENARIOS):
                age_days = user_index * 6 + scenario_index
                created_at = now - timedelta(days=age_days, hours=scenario_index)
                conversation_id = self._upsert_conversation(
                    user_id=user_id,
                    title=scenario["title"],
                    created_at=created_at,
                )
                conversation_ids.append(conversation_id)
                self._upsert_message(
                    conversation_id,
                    1,
                    "assistant",
                    ASSISTANT_GREETING,
                    created_at,
                )
                trigger_id = self._upsert_message(
                    conversation_id,
                    2,
                    "user",
                    scenario["prompt"],
                    created_at + timedelta(minutes=1),
                )

                if scenario_index >= 4:
                    self._upsert_message(
                        conversation_id,
                        3,
                        "assistant",
                        "Zapisuję ten kontekst. Rekomendacje zostaną przygotowane przy kolejnym uruchomieniu.",
                        created_at + timedelta(minutes=2),
                    )
                    self._upsert_message(
                        conversation_id,
                        4,
                        "system",
                        "Rozmowa demonstracyjna bez uruchomionego procesu rekomendacji.",
                        created_at + timedelta(minutes=3),
                    )
                    continue

                request_id = self._upsert_request(
                    conversation_id,
                    trigger_id,
                    scenario,
                    created_at + timedelta(minutes=1, seconds=5),
                )
                run_id = self._upsert_run(
                    request_id,
                    created_at + timedelta(minutes=1, seconds=6),
                )
                selected_content_ids = [
                    content_ids[(history_index * 3 + offset) % len(content_ids)]
                    for offset in range(3)
                ]
                for rank, content_id in enumerate(selected_content_ids, start=1):
                    candidate_id = self._upsert_candidate(
                        run_id,
                        content_id,
                        rank,
                        created_at + timedelta(minutes=1, seconds=8 + rank),
                    )
                    candidates.append((candidate_id, content_id))
                self._upsert_agent_executions(
                    run_id,
                    scenario,
                    selected_content_ids,
                    created_at + timedelta(minutes=1, seconds=6),
                )
                self._upsert_message(
                    conversation_id,
                    3,
                    "assistant",
                    ASSISTANT_RESPONSE,
                    created_at + timedelta(minutes=2),
                )
                self._upsert_message(
                    conversation_id,
                    4,
                    "system",
                    f"Proces rekomendacji zakończony: run_id={run_id}.",
                    created_at + timedelta(minutes=2, seconds=1),
                )
                history_index += 1
        return conversation_ids, candidates

    def _upsert_conversation(self, *, user_id: int, title: str, created_at) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM conversation
                WHERE user_id = %s AND title = %s
                ORDER BY id
                LIMIT 1
                """,
                [user_id, title],
            )
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    "UPDATE conversation SET updated_at = %s WHERE id = %s",
                    [created_at + timedelta(minutes=2), row[0]],
                )
                return row[0]
            cursor.execute(
                """
                INSERT INTO conversation (user_id, title, created_at, updated_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                [user_id, title, created_at, created_at + timedelta(minutes=2)],
            )
            return cursor.fetchone()[0]

    def _upsert_message(
        self,
        conversation_id: int,
        sequence_no: int,
        role: str,
        content: str,
        created_at,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO message (
                    conversation_id, role, content, sequence_no, created_at
                )
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (conversation_id, sequence_no) DO UPDATE SET
                    role = EXCLUDED.role,
                    content = EXCLUDED.content,
                    created_at = EXCLUDED.created_at
                RETURNING id
                """,
                [conversation_id, role, content, sequence_no, created_at],
            )
            return cursor.fetchone()[0]

    def _upsert_request(
        self,
        conversation_id: int,
        trigger_message_id: int,
        scenario: dict[str, Any],
        created_at,
    ) -> int:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM recommendation_request
                WHERE conversation_id = %s AND trigger_message_id = %s
                ORDER BY id
                LIMIT 1
                """,
                [conversation_id, trigger_message_id],
            )
            row = cursor.fetchone()
            values = [
                scenario["mood"],
                Jsonb(scenario["context"]),
                Jsonb(scenario["constraints"]),
                created_at,
            ]
            if row:
                cursor.execute(
                    """
                    UPDATE recommendation_request
                    SET mood = %s, extracted_context = %s, constraints = %s,
                        created_at = %s
                    WHERE id = %s
                    """,
                    [*values, row[0]],
                )
                return row[0]
            cursor.execute(
                """
                INSERT INTO recommendation_request (
                    conversation_id, trigger_message_id, mood, extracted_context,
                    constraints, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                [conversation_id, trigger_message_id, *values],
            )
            return cursor.fetchone()[0]

    def _upsert_run(self, request_id: int, started_at) -> int:
        finished_at = started_at + timedelta(seconds=3)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM recommendation_run
                WHERE request_id = %s
                ORDER BY id
                LIMIT 1
                """,
                [request_id],
            )
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    """
                    UPDATE recommendation_run
                    SET status = 'completed', graph_version = 'seed-v1',
                        model_name = 'demo-agent-pipeline', started_at = %s,
                        finished_at = %s
                    WHERE id = %s
                    """,
                    [started_at, finished_at, row[0]],
                )
                return row[0]
            cursor.execute(
                """
                INSERT INTO recommendation_run (
                    request_id, status, graph_version, model_name,
                    started_at, finished_at
                )
                VALUES (%s, 'completed', 'seed-v1', 'demo-agent-pipeline', %s, %s)
                RETURNING id
                """,
                [request_id, started_at, finished_at],
            )
            return cursor.fetchone()[0]

    def _upsert_candidate(
        self,
        run_id: int,
        content_id: int,
        rank: int,
        created_at,
    ) -> int:
        final_score = 0.97 - rank * 0.035
        relevance_score = min(0.99, final_score + 0.02)
        critic_score = max(0.70, final_score - 0.01)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO run_candidate (
                    run_id, content_id, source_rank, relevance_score,
                    critic_score, final_score, status, final_rank,
                    decision_reason, explanation, metadata_snapshot, created_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, 'selected', %s, %s, %s, %s, %s
                )
                ON CONFLICT (run_id, content_id) DO UPDATE SET
                    source_rank = EXCLUDED.source_rank,
                    relevance_score = EXCLUDED.relevance_score,
                    critic_score = EXCLUDED.critic_score,
                    final_score = EXCLUDED.final_score,
                    status = EXCLUDED.status,
                    final_rank = EXCLUDED.final_rank,
                    decision_reason = EXCLUDED.decision_reason,
                    explanation = EXCLUDED.explanation,
                    metadata_snapshot = EXCLUDED.metadata_snapshot,
                    created_at = EXCLUDED.created_at
                RETURNING id
                """,
                [
                    run_id,
                    content_id,
                    rank + 1,
                    relevance_score,
                    critic_score,
                    final_score,
                    rank,
                    "Wysoka zgodność z nastrojem, ograniczeniami i profilem użytkownika.",
                    (
                        "Tytuł łączy oczekiwany klimat z preferowanym tempem narracji "
                        "i uzyskał wysoką ocenę w rankingu demonstracyjnym."
                    ),
                    Jsonb({"seeded": True, "rank": rank}),
                    created_at,
                ],
            )
            return cursor.fetchone()[0]

    def _upsert_agent_executions(
        self,
        run_id: int,
        scenario: dict[str, Any],
        content_ids: list[int],
        started_at,
    ):
        with connection.cursor() as cursor:
            for sequence_no, (agent_type, activity) in enumerate(AGENTS, start=1):
                agent_started_at = started_at + timedelta(milliseconds=(sequence_no - 1) * 650)
                duration_ms = 420 + sequence_no * 95
                cursor.execute(
                    """
                    INSERT INTO agent_execution (
                        run_id, agent_type, sequence_no, status, input_snapshot,
                        output_snapshot, duration_ms, started_at, finished_at
                    )
                    VALUES (%s, %s, %s, 'success', %s, %s, %s, %s, %s)
                    ON CONFLICT (run_id, sequence_no) DO UPDATE SET
                        agent_type = EXCLUDED.agent_type,
                        status = EXCLUDED.status,
                        input_snapshot = EXCLUDED.input_snapshot,
                        output_snapshot = EXCLUDED.output_snapshot,
                        duration_ms = EXCLUDED.duration_ms,
                        started_at = EXCLUDED.started_at,
                        finished_at = EXCLUDED.finished_at
                    """,
                    [
                        run_id,
                        agent_type,
                        sequence_no,
                        Jsonb(
                            {
                                "mood": scenario["mood"],
                                "constraints": scenario["constraints"],
                            }
                        ),
                        Jsonb(
                            {
                                "activity": activity,
                                "candidateContentIds": content_ids,
                            }
                        ),
                        duration_ms,
                        agent_started_at,
                        agent_started_at + timedelta(milliseconds=duration_ms),
                    ],
                )

    def _seed_interactions(
        self,
        user_ids: list[int],
        content_ids: list[int],
        candidates: list[tuple[int, int]],
    ):
        now = timezone.now()
        random_generator = random.Random(20260723)
        interaction_types = (
            "details_opened",
            "watchlisted",
            "watched",
            "liked",
            "rated",
            "disliked",
        )
        with connection.cursor() as cursor:
            for user_index, user_id in enumerate(user_ids):
                for interaction_index in range(30):
                    seed_key = f"demo-u{user_index + 1}-i{interaction_index + 1}"
                    interaction_type = interaction_types[interaction_index % len(interaction_types)]
                    if interaction_index < 12:
                        source_candidate_id, content_id = candidates[
                            (user_index * 11 + interaction_index) % len(candidates)
                        ]
                    else:
                        source_candidate_id = None
                        content_id = content_ids[
                            (user_index * 37 + interaction_index * 7) % len(content_ids)
                        ]
                    rating = (
                        round(random_generator.uniform(6.5, 9.5), 1)
                        if interaction_type == "rated"
                        else None
                    )
                    created_at = now - timedelta(
                        days=user_index * 4 + interaction_index,
                        hours=interaction_index % 8,
                    )
                    metadata = Jsonb(
                        {
                            "seed_key": seed_key,
                            "source": "demo-seeder",
                        }
                    )
                    cursor.execute(
                        """
                        SELECT id FROM interaction
                        WHERE user_id = %s AND metadata ->> 'seed_key' = %s
                        ORDER BY id
                        LIMIT 1
                        """,
                        [user_id, seed_key],
                    )
                    row = cursor.fetchone()
                    values = [
                        content_id,
                        source_candidate_id,
                        interaction_type,
                        rating,
                        metadata,
                        created_at,
                    ]
                    if row:
                        cursor.execute(
                            """
                            UPDATE interaction
                            SET content_id = %s, source_candidate_id = %s,
                                interaction_type = %s, rating = %s, metadata = %s,
                                created_at = %s
                            WHERE id = %s
                            """,
                            [*values, row[0]],
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO interaction (
                                user_id, content_id, source_candidate_id,
                                interaction_type, rating, metadata, created_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            [user_id, *values],
                        )

    def _seeded_counts(self) -> dict[str, int]:
        tables = (
            "app_user",
            "user_profile",
            "user_preference",
            "conversation",
            "message",
            "recommendation_request",
            "recommendation_run",
            "content",
            "genre",
            "content_genre",
            "run_candidate",
            "interaction",
            "agent_execution",
            "content_embedding",
        )
        counts: dict[str, int] = {}
        with connection.cursor() as cursor:
            for table in tables:
                cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                counts[table] = cursor.fetchone()[0]
        return counts
