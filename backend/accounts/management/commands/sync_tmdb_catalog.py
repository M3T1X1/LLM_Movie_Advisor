import os
from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from backend.api.catalog_sync import upsert_catalog
from backend.api.models import Content
from backend.redis import TMDB_CATALOG_LOCK_KEY, run_with_redis_lock
from backend.tmdb import TmdbClient


DEFAULT_BASELINE_MOVIES = 2000
DEFAULT_BASELINE_TV_SHOWS = 2000
DEFAULT_DAYS_BACK = 30
DEFAULT_MAX_PAGES = 10
DEFAULT_UPCOMING_DAYS_AHEAD = 365
DEFAULT_UPCOMING_MAX_PAGES = 10


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value in {None, ""}:
        return default
    try:
        return int(value)
    except ValueError as error:
        raise CommandError(f"{name} must be an integer.") from error


class Command(BaseCommand):
    help = (
        "Ensures the initial TMDB catalog size and synchronizes newly released "
        "titles and upcoming movies without creating demo data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--baseline-movies",
            type=int,
            default=env_int(
                "TMDB_BASELINE_MOVIES",
                DEFAULT_BASELINE_MOVIES,
            ),
            help="Minimum number of released movies in the catalog.",
        )
        parser.add_argument(
            "--baseline-tv-shows",
            type=int,
            default=env_int(
                "TMDB_BASELINE_TV_SHOWS",
                DEFAULT_BASELINE_TV_SHOWS,
            ),
            help="Minimum number of released TV shows in the catalog.",
        )
        parser.add_argument(
            "--days-back",
            type=int,
            default=env_int("TMDB_SYNC_DAYS_BACK", DEFAULT_DAYS_BACK),
            help="Include releases from this many days in the past.",
        )
        parser.add_argument(
            "--max-pages",
            type=int,
            default=env_int("TMDB_SYNC_MAX_PAGES", DEFAULT_MAX_PAGES),
            help="Maximum discover pages fetched per media type.",
        )
        parser.add_argument(
            "--upcoming-days-ahead",
            type=int,
            default=env_int(
                "TMDB_UPCOMING_DAYS_AHEAD",
                DEFAULT_UPCOMING_DAYS_AHEAD,
            ),
            help="How many days ahead to synchronize upcoming movies.",
        )
        parser.add_argument(
            "--upcoming-max-pages",
            type=int,
            default=env_int(
                "TMDB_UPCOMING_MAX_PAGES",
                DEFAULT_UPCOMING_MAX_PAGES,
            ),
            help="Maximum discover pages fetched for upcoming movies.",
        )

    def handle(self, *args, **options):
        baseline_movies = options["baseline_movies"]
        baseline_tv_shows = options["baseline_tv_shows"]
        days_back = options["days_back"]
        max_pages = options["max_pages"]
        upcoming_days_ahead = options["upcoming_days_ahead"]
        upcoming_max_pages = options["upcoming_max_pages"]
        if not 0 <= baseline_movies <= 10000:
            raise CommandError("--baseline-movies must be between 0 and 10000.")
        if not 0 <= baseline_tv_shows <= 10000:
            raise CommandError("--baseline-tv-shows must be between 0 and 10000.")
        if not 0 <= days_back <= 3650:
            raise CommandError("--days-back must be between 0 and 3650.")
        if not 1 <= max_pages <= 500:
            raise CommandError("--max-pages must be between 1 and 500.")
        if not 0 <= upcoming_days_ahead <= 3650:
            raise CommandError(
                "--upcoming-days-ahead must be between 0 and 3650."
            )
        if not 1 <= upcoming_max_pages <= 500:
            raise CommandError(
                "--upcoming-max-pages must be between 1 and 500."
            )

        today = date.today()
        start_date = today - timedelta(days=days_back)
        upcoming_end_date = today + timedelta(days=upcoming_days_ahead)
        synchronized_counts = {
            "bootstrap_movies": 0,
            "bootstrap_tv": 0,
            "released": 0,
            "upcoming": 0,
        }

        def synchronize() -> None:
            client = TmdbClient(
                api_key=os.environ.get("TMDB_API_KEY"),
                access_token=os.environ.get("TMDB_API_TOKEN"),
            )
            genres = client.fetch_genres()
            catalog_by_identity = {}

            baseline_targets = (
                ("movie", baseline_movies, "bootstrap_movies"),
                ("tv", baseline_tv_shows, "bootstrap_tv"),
            )
            for media_type, target, counter_name in baseline_targets:
                released_count = Content.objects.filter(
                    media_type=media_type,
                    release_date__lte=today,
                ).count()
                if released_count >= target:
                    continue
                self.stdout.write(
                    f"Preparing initial {media_type} catalog: "
                    f"{released_count}/{target} released titles..."
                )
                items = client.fetch_popular_catalog(
                    media_type=media_type,
                    target_count=target,
                    released_through=today,
                )
                synchronized_counts[counter_name] = len(items)
                catalog_by_identity.update(
                    {
                        (item.media_type, item.tmdb_id): item
                        for item in items
                    }
                )

            self.stdout.write(
                "Synchronizing TMDB releases from "
                f"{start_date.isoformat()} to {today.isoformat()}..."
            )
            released_items = client.fetch_release_catalog(
                start_date=start_date,
                end_date=today,
                max_pages=max_pages,
            )
            synchronized_counts["released"] = len(released_items)
            catalog_by_identity.update(
                {
                    (item.media_type, item.tmdb_id): item
                    for item in released_items
                }
            )

            if upcoming_days_ahead:
                self.stdout.write(
                    "Synchronizing upcoming TMDB movies from "
                    f"{today.isoformat()} to {upcoming_end_date.isoformat()}..."
                )
                upcoming_items = client.fetch_release_catalog(
                    start_date=today,
                    end_date=upcoming_end_date,
                    max_pages=upcoming_max_pages,
                    media_types=("movie",),
                )
                synchronized_counts["upcoming"] = len(upcoming_items)
                catalog_by_identity.update(
                    {
                        (item.media_type, item.tmdb_id): item
                        for item in upcoming_items
                    }
                )

            catalog = list(catalog_by_identity.values())
            if not catalog:
                self.stdout.write(
                    self.style.WARNING("TMDB returned no valid catalog items.")
                )
                return
            with transaction.atomic():
                upsert_catalog(genres, catalog)

        executed = run_with_redis_lock(
            TMDB_CATALOG_LOCK_KEY,
            synchronize,
            timeout=settings.TMDB_CATALOG_LOCK_TIMEOUT,
        )
        if not executed:
            self.stdout.write(
                self.style.WARNING(
                    "Catalog synchronization skipped because another run is active."
                )
            )
            return
        self.stdout.write(
            self.style.SUCCESS(
                "TMDB catalog synchronization finished: "
                f"bootstrap movies={synchronized_counts['bootstrap_movies']}, "
                f"bootstrap TV={synchronized_counts['bootstrap_tv']}, "
                f"released={synchronized_counts['released']}, "
                f"upcoming={synchronized_counts['upcoming']}."
            )
        )
