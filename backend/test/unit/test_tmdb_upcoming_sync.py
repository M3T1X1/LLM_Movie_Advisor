from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from backend.api.views import sync_upcoming_from_tmdb


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
)
class UpcomingSynchronizationTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        lock_patcher = patch(
            "backend.api.views.sync_from_tmdb",
            side_effect=lambda operation: operation() or True,
        )
        self.mocked_sync_from_tmdb = lock_patcher.start()
        self.addCleanup(lock_patcher.stop)

    @patch("backend.api.views.transaction.atomic")
    @patch("backend.api.views.SeedDemoCommand")
    @patch("backend.api.views.TmdbClient")
    def test_sync_fetches_two_polish_pages_deduplicates_and_seeds(
        self,
        mocked_client_class,
        mocked_command_class,
        mocked_atomic,
    ):
        client = mocked_client_class.return_value
        client.fetch_genres.return_value = {18: "Dramat"}
        client.get.side_effect = [
            {
                "results": [
                    {
                        "id": 1,
                        "title": "Pierwszy",
                        "release_date": "2026-08-01",
                        "genre_ids": [18],
                    },
                    {"id": 2},
                ]
            },
            {
                "results": [
                    {
                        "id": 1,
                        "title": "Pierwszy zduplikowany",
                        "release_date": "2026-08-01",
                        "genre_ids": [18],
                    },
                    {
                        "id": 3,
                        "title": "Trzeci",
                        "release_date": "2026-09-01",
                        "genre_ids": [18],
                    },
                ]
            },
        ]
        mocked_atomic.return_value.__enter__.return_value = None

        sync_upcoming_from_tmdb(force_refresh=True)

        self.assertEqual(client.get.call_count, 2)
        for page, call in enumerate(client.get.call_args_list, start=1):
            self.assertEqual(call.args, ("/movie/upcoming",))
            self.assertEqual(
                call.kwargs,
                {"language": "pl-PL", "region": "PL", "page": page},
            )
        genres, items = mocked_command_class.return_value._seed_catalog.call_args.args
        self.assertEqual(genres, {18: "Dramat"})
        self.assertEqual({item.tmdb_id for item in items}, {1, 3})
        self.assertEqual(
            next(item for item in items if item.tmdb_id == 1).title,
            "Pierwszy zduplikowany",
        )
        self.assertEqual(
            next(item for item in items if item.tmdb_id == 3).release_date,
            date(2026, 9, 1),
        )

    @patch("backend.api.views.SeedDemoCommand")
    @patch("backend.api.views.TmdbClient")
    def test_sync_does_not_seed_when_tmdb_has_no_valid_items(
        self,
        mocked_client_class,
        mocked_command_class,
    ):
        client = mocked_client_class.return_value
        client.fetch_genres.return_value = {18: "Dramat"}
        client.get.side_effect = [
            {"results": [{"id": 1}]},
            {"results": "invalid"},
        ]

        sync_upcoming_from_tmdb(force_refresh=True)

        mocked_command_class.return_value._seed_catalog.assert_not_called()

