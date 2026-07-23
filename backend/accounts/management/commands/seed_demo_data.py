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

from backend.api.models import (
    AgentExecution,
    AgentStatus,
    BusinessUser,
    CandidateStatus,
    Content,
    ContentEmbedding,
    ContentGenre,
    Conversation,
    Genre,
    Interaction,
    Message,
    RecommendationRequest,
    RecommendationRun,
    RunCandidate,
    RunStatus,
    UserPreference,
    UserProfile,
)


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

            business_user = BusinessUser.objects.filter(
                username=definition["username"]
            ).first()
            if business_user is None:
                business_user = BusinessUser.objects.filter(
                    email=definition["email"]
                ).first()
            if business_user is None:
                business_user = BusinessUser(date_joined=now)
            business_user.email = definition["email"]
            business_user.username = definition["username"]
            business_user.password = auth_user.password
            business_user.is_active = True
            business_user.save()
            UserProfile.objects.update_or_create(
                user=business_user,
                defaults={
                    "semantic_summary": definition["summary"],
                    "version": 1,
                    "last_rebuilt_at": now,
                    "updated_at": now,
                },
            )
            for (
                preference_type,
                preference_value,
                polarity,
                weight,
                confidence,
            ) in definition["preferences"]:
                UserPreference.objects.update_or_create(
                    user=business_user,
                    preference_type=preference_type,
                    preference_value=preference_value,
                    defaults={
                        "polarity": polarity,
                        "weight": weight,
                        "confidence": confidence,
                        "updated_at": now,
                    },
                    create_defaults={
                        "polarity": polarity,
                        "weight": weight,
                        "confidence": confidence,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
            business_ids.append(business_user.pk)
        return business_ids

    def _seed_catalog(
        self,
        genres: dict[int, str],
        catalog: list[TmdbCatalogItem],
    ) -> list[int]:
        now = timezone.now()
        genre_objects: dict[int, Genre] = {}
        content_ids: list[int] = []
        for tmdb_genre_id, name in sorted(genres.items()):
            genre, _ = Genre.objects.update_or_create(
                tmdb_genre_id=tmdb_genre_id,
                defaults={"name": name[:100]},
            )
            genre_objects[tmdb_genre_id] = genre

        for item in catalog:
            content, _ = Content.objects.update_or_create(
                tmdb_id=item.tmdb_id,
                media_type=item.media_type,
                defaults={
                    "title": item.title,
                    "original_title": item.original_title,
                    "overview": item.overview,
                    "release_date": item.release_date,
                    "original_language": item.original_language,
                    "poster_path": item.poster_path,
                    "vote_average": item.vote_average,
                    "popularity": item.popularity,
                    "metadata": item.metadata,
                    "tmdb_refreshed_at": now,
                },
            )
            content_ids.append(content.pk)
            ContentGenre.objects.filter(content=content).delete()
            ContentGenre.objects.bulk_create(
                [
                    ContentGenre(
                        content=content,
                        genre=genre_objects[tmdb_genre_id],
                    )
                    for tmdb_genre_id in item.genre_ids
                    if tmdb_genre_id in genre_objects
                ],
                ignore_conflicts=True,
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
        conversation = (
            Conversation.objects.filter(user_id=user_id, title=title)
            .order_by("id")
            .first()
        )
        if conversation is None:
            conversation = Conversation(
                user_id=user_id,
                title=title,
                created_at=created_at,
            )
        conversation.updated_at = created_at + timedelta(minutes=2)
        conversation.save()
        return conversation.pk

    def _upsert_message(
        self,
        conversation_id: int,
        sequence_no: int,
        role: str,
        content: str,
        created_at,
    ) -> int:
        message, _ = Message.objects.update_or_create(
            conversation_id=conversation_id,
            sequence_no=sequence_no,
            defaults={
                "role": role,
                "content": content,
                "created_at": created_at,
            },
        )
        return message.pk

    def _upsert_request(
        self,
        conversation_id: int,
        trigger_message_id: int,
        scenario: dict[str, Any],
        created_at,
    ) -> int:
        request = (
            RecommendationRequest.objects.filter(
                conversation_id=conversation_id,
                trigger_message_id=trigger_message_id,
            )
            .order_by("id")
            .first()
        )
        if request is None:
            request = RecommendationRequest(
                conversation_id=conversation_id,
                trigger_message_id=trigger_message_id,
            )
        request.mood = scenario["mood"]
        request.extracted_context = scenario["context"]
        request.constraints = scenario["constraints"]
        request.created_at = created_at
        request.save()
        return request.pk

    def _upsert_run(self, request_id: int, started_at) -> int:
        finished_at = started_at + timedelta(seconds=3)
        run = RecommendationRun.objects.filter(request_id=request_id).order_by(
            "id"
        ).first()
        if run is None:
            run = RecommendationRun(request_id=request_id)
        run.status = RunStatus.COMPLETED
        run.graph_version = "seed-v1"
        run.model_name = "demo-agent-pipeline"
        run.started_at = started_at
        run.finished_at = finished_at
        run.save()
        return run.pk

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
        candidate, _ = RunCandidate.objects.update_or_create(
            run_id=run_id,
            content_id=content_id,
            defaults={
                "source_rank": rank + 1,
                "relevance_score": relevance_score,
                "critic_score": critic_score,
                "final_score": final_score,
                "status": CandidateStatus.SELECTED,
                "final_rank": rank,
                "decision_reason": (
                    "Wysoka zgodność z nastrojem, ograniczeniami i profilem użytkownika."
                ),
                "explanation": (
                    "Tytuł łączy oczekiwany klimat z preferowanym tempem narracji "
                    "i uzyskał wysoką ocenę w rankingu demonstracyjnym."
                ),
                "metadata_snapshot": {"seeded": True, "rank": rank},
                "created_at": created_at,
            },
        )
        return candidate.pk

    def _upsert_agent_executions(
        self,
        run_id: int,
        scenario: dict[str, Any],
        content_ids: list[int],
        started_at,
    ):
        for sequence_no, (agent_type, activity) in enumerate(AGENTS, start=1):
            agent_started_at = started_at + timedelta(
                milliseconds=(sequence_no - 1) * 650
            )
            duration_ms = 420 + sequence_no * 95
            AgentExecution.objects.update_or_create(
                run_id=run_id,
                sequence_no=sequence_no,
                defaults={
                    "agent_type": agent_type,
                    "status": AgentStatus.SUCCESS,
                    "input_snapshot": {
                        "mood": scenario["mood"],
                        "constraints": scenario["constraints"],
                    },
                    "output_snapshot": {
                        "activity": activity,
                        "candidateContentIds": content_ids,
                    },
                    "duration_ms": duration_ms,
                    "started_at": agent_started_at,
                    "finished_at": agent_started_at
                    + timedelta(milliseconds=duration_ms),
                },
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
        for user_index, user_id in enumerate(user_ids):
            for interaction_index in range(30):
                seed_key = f"demo-u{user_index + 1}-i{interaction_index + 1}"
                interaction_type = interaction_types[
                    interaction_index % len(interaction_types)
                ]
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
                metadata = {
                    "seed_key": seed_key,
                    "source": "demo-seeder",
                }
                interaction = (
                    Interaction.objects.filter(
                        user_id=user_id,
                        metadata__seed_key=seed_key,
                    )
                    .order_by("id")
                    .first()
                )
                if interaction is None:
                    interaction = Interaction(user_id=user_id)
                interaction.content_id = content_id
                interaction.source_candidate_id = source_candidate_id
                interaction.interaction_type = interaction_type
                interaction.rating = rating
                interaction.metadata = metadata
                interaction.created_at = created_at
                interaction.save()

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
        model_by_table = {
            "app_user": BusinessUser,
            "user_profile": UserProfile,
            "user_preference": UserPreference,
            "conversation": Conversation,
            "message": Message,
            "recommendation_request": RecommendationRequest,
            "recommendation_run": RecommendationRun,
            "content": Content,
            "genre": Genre,
            "content_genre": ContentGenre,
            "run_candidate": RunCandidate,
            "interaction": Interaction,
            "agent_execution": AgentExecution,
            "content_embedding": ContentEmbedding,
        }
        return {table: model_by_table[table].objects.count() for table in tables}
