import json
import time
from dataclasses import dataclass
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.management.base import CommandError


TMDB_API_URL = "https://api.themoviedb.org/3"
TMDB_MAX_PAGES = 500


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
                raise CommandError(
                    f"TMDB request failed for {path}: {error}"
                ) from error

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

    def fetch_release_catalog(
        self,
        *,
        start_date: date,
        end_date: date,
        max_pages: int,
        media_types: tuple[str, ...] = ("movie", "tv"),
    ) -> list[TmdbCatalogItem]:
        if start_date > end_date:
            raise CommandError(
                "TMDB synchronization start date must not exceed end date."
            )
        if not 1 <= max_pages <= TMDB_MAX_PAGES:
            raise CommandError(
                f"TMDB synchronization pages must be between 1 and {TMDB_MAX_PAGES}."
            )
        if not media_types or any(
            media_type not in {"movie", "tv"} for media_type in media_types
        ):
            raise CommandError("TMDB media types must contain movie or tv.")

        catalog: list[TmdbCatalogItem] = []
        seen: set[tuple[str, int]] = set()
        for media_type in dict.fromkeys(media_types):
            for item in self._fetch_release_pages(
                media_type,
                start_date=start_date,
                end_date=end_date,
                max_pages=max_pages,
            ):
                identity = (item.media_type, item.tmdb_id)
                if identity in seen:
                    continue
                catalog.append(item)
                seen.add(identity)
        return catalog

    def fetch_popular_catalog(
        self,
        *,
        media_type: str,
        target_count: int,
        released_through: date,
    ) -> list[TmdbCatalogItem]:
        if media_type not in {"movie", "tv"}:
            raise CommandError("TMDB media type must be movie or tv.")
        if not 0 <= target_count <= TMDB_MAX_PAGES * 20:
            raise CommandError(
                "TMDB popular catalog target must be between 0 and "
                f"{TMDB_MAX_PAGES * 20}."
            )
        if target_count == 0:
            return []

        items: list[TmdbCatalogItem] = []
        seen_ids: set[int] = set()
        available_pages = TMDB_MAX_PAGES
        for page in range(1, TMDB_MAX_PAGES + 1):
            payload = self.get(
                f"/{media_type}/popular",
                language="pl-PL",
                page=page,
                region="PL" if media_type == "movie" else None,
            )
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

            for raw_item in results:
                item = normalize_tmdb_item(raw_item, media_type)
                if (
                    item is None
                    or item.tmdb_id in seen_ids
                    or item.release_date is None
                    or item.release_date > released_through
                ):
                    continue
                items.append(item)
                seen_ids.add(item.tmdb_id)
                if len(items) >= target_count:
                    return items

            if not results or page >= available_pages:
                break

        raise CommandError(
            f"TMDB returned only {len(items)} released {media_type} items; "
            f"{target_count} required for the initial catalog."
        )

    def _fetch_release_pages(
        self,
        media_type: str,
        *,
        start_date: date,
        end_date: date,
        max_pages: int,
    ) -> list[TmdbCatalogItem]:
        items: list[TmdbCatalogItem] = []
        available_pages = max_pages
        for page in range(1, max_pages + 1):
            common_params = {
                "language": "pl-PL",
                "page": page,
                "sort_by": "popularity.desc",
                "include_adult": "false",
            }
            if media_type == "movie":
                payload = self.get(
                    "/discover/movie",
                    region="PL",
                    **{
                        **common_params,
                        "release_date.gte": start_date.isoformat(),
                        "release_date.lte": end_date.isoformat(),
                        "with_release_type": "2|3|4|5|6",
                    },
                )
            else:
                payload = self.get(
                    "/discover/tv",
                    **{
                        **common_params,
                        "first_air_date.gte": start_date.isoformat(),
                        "first_air_date.lte": end_date.isoformat(),
                        "include_null_first_air_dates": "false",
                    },
                )

            results = payload.get("results")
            if not isinstance(results, list):
                raise CommandError(
                    f"TMDB returned an invalid discover {media_type} response."
                )
            reported_total_pages = payload.get("total_pages")
            if (
                isinstance(reported_total_pages, int)
                and not isinstance(reported_total_pages, bool)
                and reported_total_pages > 0
            ):
                available_pages = min(reported_total_pages, max_pages, TMDB_MAX_PAGES)

            for raw_item in results:
                item = normalize_tmdb_item(raw_item, media_type)
                if item is not None:
                    items.append(item)
            if not results or page >= available_pages:
                break
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
