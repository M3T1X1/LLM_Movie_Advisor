from django.db import transaction
from django.utils import timezone

from backend.api.genre_normalization import canonical_genre_ids, canonical_genres
from backend.api.models import Content, ContentGenre, Genre
from backend.redis import invalidate_catalog_search_cache
from backend.tmdb import TmdbCatalogItem


def upsert_catalog(
    genres: dict[int, str],
    catalog: list[TmdbCatalogItem],
) -> list[int]:
    now = timezone.now()
    genre_objects: dict[int, Genre] = {}
    content_ids: list[int] = []
    for tmdb_genre_id, name in sorted(canonical_genres(genres).items()):
        genre, _ = Genre.objects.update_or_create(
            tmdb_genre_id=tmdb_genre_id,
            defaults={"name": name[:100]},
        )
        genre_objects[tmdb_genre_id] = genre

    for item in catalog:
        existing_metadata = (
            Content.objects.filter(
                tmdb_id=item.tmdb_id,
                media_type=item.media_type,
            )
            .values_list("metadata", flat=True)
            .first()
            or {}
        )
        incoming_metadata = dict(item.metadata)
        # Discovery responses for movies omit countries; keep enriched details.
        if not incoming_metadata.get("originCountry") and existing_metadata.get("originCountry"):
            incoming_metadata.pop("originCountry", None)
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
                "metadata": {**existing_metadata, **incoming_metadata},
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
                for tmdb_genre_id in canonical_genre_ids(item.genre_ids)
                if tmdb_genre_id in genre_objects
            ],
            ignore_conflicts=True,
        )
    transaction.on_commit(invalidate_catalog_search_cache)
    return content_ids
