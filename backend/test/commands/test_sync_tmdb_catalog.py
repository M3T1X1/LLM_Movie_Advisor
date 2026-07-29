from datetime import date, timedelta
from unittest.mock import MagicMock, call, patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from backend.accounts.management.commands.sync_tmdb_catalog import Command


class SyncTmdbCatalogCommandTests(SimpleTestCase):
    def setUp(self):
        self.command = Command()
        self.command.stdout = MagicMock()

    @patch(
        "backend.accounts.management.commands.sync_tmdb_catalog.TmdbClient"
    )
    def test_rejects_invalid_limits_before_contacting_tmdb(
        self,
        mocked_client_class,
    ):
        valid_options = {
            "baseline_movies": 2000,
            "baseline_tv_shows": 2000,
            "days_back": 30,
            "max_pages": 10,
            "upcoming_days_ahead": 365,
            "upcoming_max_pages": 10,
        }
        invalid_options = (
            {**valid_options, "baseline_movies": -1},
            {**valid_options, "baseline_tv_shows": 10001},
            {**valid_options, "days_back": -1},
            {**valid_options, "max_pages": 0},
            {**valid_options, "max_pages": 501},
            {**valid_options, "upcoming_days_ahead": -1},
            {**valid_options, "upcoming_max_pages": 0},
            {**valid_options, "upcoming_max_pages": 501},
        )

        for options in invalid_options:
            with self.subTest(options=options):
                with self.assertRaises(CommandError):
                    self.command.handle(**options)

        mocked_client_class.assert_not_called()

    @patch(
        "backend.accounts.management.commands.sync_tmdb_catalog.transaction.atomic"
    )
    @patch(
        "backend.accounts.management.commands.sync_tmdb_catalog.Content.objects"
    )
    @patch(
        "backend.accounts.management.commands.sync_tmdb_catalog.upsert_catalog"
    )
    @patch(
        "backend.accounts.management.commands.sync_tmdb_catalog.TmdbClient"
    )
    @patch(
        "backend.accounts.management.commands.sync_tmdb_catalog.run_with_redis_lock",
        side_effect=lambda key, operation, **kwargs: operation() or True,
    )
    def test_synchronizes_release_window_without_demo_data(
        self,
        mocked_lock,
        mocked_client_class,
        mocked_upsert_catalog,
        mocked_content_objects,
        mocked_atomic,
    ):
        client = mocked_client_class.return_value
        released_item = MagicMock(media_type="movie", tmdb_id=1)
        upcoming_item = MagicMock(media_type="movie", tmdb_id=2)
        client.fetch_genres.return_value = {18: "Dramat"}
        client.fetch_release_catalog.side_effect = [
            [released_item],
            [upcoming_item],
        ]
        mocked_content_objects.filter.return_value.count.return_value = 2000
        mocked_atomic.return_value.__enter__.return_value = None

        self.command.handle(
            baseline_movies=2000,
            baseline_tv_shows=2000,
            days_back=7,
            max_pages=4,
            upcoming_days_ahead=90,
            upcoming_max_pages=3,
        )

        mocked_lock.assert_called_once()
        self.assertEqual(mocked_lock.call_args.args[0], "lock:tmdb:catalog")
        self.assertEqual(mocked_lock.call_args.kwargs, {"timeout": 1800})
        client.fetch_genres.assert_called_once_with()
        self.assertEqual(
            client.fetch_release_catalog.call_args_list,
            [
                call(
                    start_date=date.today() - timedelta(days=7),
                    end_date=date.today(),
                    max_pages=4,
                ),
                call(
                    start_date=date.today(),
                    end_date=date.today() + timedelta(days=90),
                    max_pages=3,
                    media_types=("movie",),
                ),
            ],
        )
        genres, items = mocked_upsert_catalog.call_args.args
        self.assertEqual(genres, {18: "Dramat"})
        self.assertEqual(items, [released_item, upcoming_item])

    @patch(
        "backend.accounts.management.commands.sync_tmdb_catalog.transaction.atomic"
    )
    @patch(
        "backend.accounts.management.commands.sync_tmdb_catalog.Content.objects"
    )
    @patch(
        "backend.accounts.management.commands.sync_tmdb_catalog.upsert_catalog"
    )
    @patch(
        "backend.accounts.management.commands.sync_tmdb_catalog.TmdbClient"
    )
    @patch(
        "backend.accounts.management.commands.sync_tmdb_catalog.run_with_redis_lock",
        side_effect=lambda key, operation, **kwargs: operation() or True,
    )
    def test_bootstraps_released_movies_and_tv_when_catalog_is_too_small(
        self,
        mocked_lock,
        mocked_client_class,
        mocked_upsert_catalog,
        mocked_content_objects,
        mocked_atomic,
    ):
        movie = MagicMock(media_type="movie", tmdb_id=10)
        tv_show = MagicMock(media_type="tv", tmdb_id=20)
        client = mocked_client_class.return_value
        client.fetch_genres.return_value = {18: "Dramat"}
        client.fetch_popular_catalog.side_effect = [[movie], [tv_show]]
        client.fetch_release_catalog.return_value = []
        mocked_content_objects.filter.return_value.count.side_effect = [0, 0]
        mocked_atomic.return_value.__enter__.return_value = None

        self.command.handle(
            baseline_movies=2000,
            baseline_tv_shows=2000,
            days_back=30,
            max_pages=10,
            upcoming_days_ahead=0,
            upcoming_max_pages=10,
        )

        self.assertEqual(
            client.fetch_popular_catalog.call_args_list,
            [
                call(
                    media_type="movie",
                    target_count=2000,
                    released_through=date.today(),
                ),
                call(
                    media_type="tv",
                    target_count=2000,
                    released_through=date.today(),
                ),
            ],
        )
        mocked_upsert_catalog.assert_called_once_with(
            {18: "Dramat"},
            [movie, tv_show],
        )

    @patch(
        "backend.accounts.management.commands.sync_tmdb_catalog.TmdbClient"
    )
    @patch(
        "backend.accounts.management.commands.sync_tmdb_catalog.run_with_redis_lock",
        return_value=False,
    )
    def test_skips_when_another_synchronization_holds_lock(
        self,
        mocked_lock,
        mocked_client_class,
    ):
        self.command.handle(
            baseline_movies=2000,
            baseline_tv_shows=2000,
            days_back=30,
            max_pages=10,
            upcoming_days_ahead=365,
            upcoming_max_pages=10,
        )

        mocked_lock.assert_called_once()
        mocked_client_class.assert_not_called()
