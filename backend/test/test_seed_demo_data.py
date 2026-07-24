import json
from io import BytesIO
from datetime import date
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from backend.accounts.management.commands.seed_demo_data import (
    Command,
    TmdbClient,
    bounded_float,
    normalize_tmdb_item,
    parse_date,
)
from backend.api.genre_normalization import canonical_genre_ids, canonical_genres


class TmdbNormalizationTests(SimpleTestCase):
    def test_splits_tmdb_tv_composite_genres_into_shared_categories(self):
        self.assertEqual(
            canonical_genres(
                {
                    10759: "Akcja i Przygoda",
                    10765: "Sci-Fi i Fantasy",
                    10768: "War & Politics",
                }
            ),
            {
                28: "Akcja",
                12: "Przygodowy",
                878: "Science Fiction",
                14: "Fantasy",
                10752: "Wojenny",
                10768: "Polityczny",
            },
        )
        self.assertEqual(
            canonical_genre_ids((10765, 14, 10759, 10768)),
            (878, 14, 28, 12, 10752, 10768),
        )

    def test_normalizes_movie_from_tmdb(self):
        item = normalize_tmdb_item(
            {
                "id": 210577,
                "title": "Zaginiona dziewczyna",
                "original_title": "Gone Girl",
                "overview": "Opis",
                "release_date": "2014-10-01",
                "original_language": "en",
                "poster_path": "/poster.jpg",
                "backdrop_path": "/backdrop.jpg",
                "vote_average": 8.1,
                "vote_count": 19000,
                "popularity": 78.4,
                "genre_ids": [18, 53, "invalid"],
                "adult": False,
            },
            "movie",
        )

        self.assertIsNotNone(item)
        self.assertEqual(item.tmdb_id, 210577)
        self.assertEqual(item.media_type, "movie")
        self.assertEqual(item.release_date, date(2014, 10, 1))
        self.assertEqual(item.genre_ids, (18, 53))
        self.assertEqual(item.metadata["source"], "tmdb")
        self.assertEqual(item.metadata["voteCount"], 19000)

    def test_normalizes_tv_show_and_rejects_invalid_rows(self):
        item = normalize_tmdb_item(
            {
                "id": 70523,
                "name": "Dark",
                "original_name": "Dark",
                "first_air_date": "2017-12-01",
                "origin_country": ["DE"],
                "genre_ids": [18, 9648],
            },
            "tv",
        )

        self.assertIsNotNone(item)
        self.assertEqual(item.title, "Dark")
        self.assertEqual(item.release_date, date(2017, 12, 1))
        self.assertEqual(item.metadata["originCountry"], ["DE"])
        self.assertIsNone(normalize_tmdb_item({"id": 1}, "movie"))
        self.assertIsNone(normalize_tmdb_item({"id": 1, "title": "Film"}, "person"))

    def test_invalid_external_values_are_safely_replaced_with_null(self):
        item = normalize_tmdb_item(
            {
                "id": 1,
                "title": "Niepełne dane",
                "release_date": "not-a-date",
                "vote_average": 14,
                "popularity": -2,
                "vote_count": -1,
                "genre_ids": None,
            },
            "movie",
        )

        self.assertIsNotNone(item)
        self.assertIsNone(item.release_date)
        self.assertIsNone(item.vote_average)
        self.assertIsNone(item.popularity)
        self.assertIsNone(item.metadata["voteCount"])
        self.assertEqual(item.genre_ids, ())
        self.assertIsNone(parse_date("2026-02-31"))
        self.assertIsNone(bounded_float(True, 0, 10))


class TmdbClientTests(SimpleTestCase):
    def test_requires_at_least_one_authentication_method(self):
        with self.assertRaisesMessage(CommandError, "TMDB credentials are required"):
            TmdbClient(api_key=None, access_token=None)

    @patch("backend.accounts.management.commands.seed_demo_data.urlopen")
    def test_uses_api_key_and_decodes_json(self, mocked_urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"genres": [{"id": 18, "name": "Dramat"}]}
        ).encode()
        mocked_urlopen.return_value = response

        payload = TmdbClient(api_key="test-key", access_token=None).get(
            "/genre/movie/list",
            language="pl-PL",
        )

        self.assertEqual(payload["genres"][0]["name"], "Dramat")
        request = mocked_urlopen.call_args.args[0]
        self.assertIn("api_key=test-key", request.full_url)
        self.assertIn("language=pl-PL", request.full_url)

    @patch("backend.accounts.management.commands.seed_demo_data.urlopen")
    def test_uses_bearer_token(self, mocked_urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"results": []}'
        mocked_urlopen.return_value = response

        TmdbClient(api_key=None, access_token="token").get("/movie/popular")

        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.headers["Authorization"], "Bearer token")

    def test_fetch_genres_merges_movie_and_tv_genres(self):
        client = TmdbClient(api_key="key", access_token=None)
        client.get = MagicMock(
            side_effect=[
                {"genres": [{"id": 18, "name": "Dramat"}, {"id": 28, "name": "Akcja"}]},
                {
                    "genres": [
                        {"id": 18, "name": "Dramat"},
                        {"id": 10765, "name": "Sci-Fi i Fantasy"},
                    ]
                },
            ]
        )

        genres = client.fetch_genres()

        self.assertEqual(
            genres,
            {18: "Dramat", 28: "Akcja", 10765: "Sci-Fi i Fantasy"},
        )
        self.assertEqual(client.get.call_count, 2)

    def test_popular_catalog_paginates_deduplicates_and_stops_at_target(self):
        client = TmdbClient(api_key="key", access_token=None)
        first_page = [
            {
                "id": item_id,
                "title": f"Film {item_id}",
                "genre_ids": [18],
            }
            for item_id in range(1, 21)
        ]
        second_page = [
            {"id": 20, "title": "Duplikat", "genre_ids": [18]},
            {"id": 21, "title": "Film 21", "genre_ids": [18]},
            {"id": 22, "title": "Film 22", "genre_ids": [18]},
        ]
        client.get = MagicMock(
            side_effect=[{"results": first_page}, {"results": second_page}]
        )

        items = client.fetch_catalog(movies=22, tv_shows=0)

        self.assertEqual(len(items), 22)
        self.assertEqual([item.tmdb_id for item in items], list(range(1, 23)))
        self.assertEqual(client.get.call_count, 2)
        self.assertEqual(client.get.call_args_list[1].kwargs["page"], 2)

    def test_popular_catalog_fetches_extra_pages_after_deduplication(self):
        client = TmdbClient(api_key="key", access_token=None)
        first_page = [
            {
                "id": item_id,
                "title": f"Film {item_id}",
                "genre_ids": [18],
            }
            for item_id in range(1, 21)
        ]
        client.get = MagicMock(
            side_effect=[
                {"results": first_page, "total_pages": 4},
                {
                    "results": [
                        {"id": 20, "title": "Duplikat 20"},
                        {"id": 21, "title": "Film 21"},
                    ],
                    "total_pages": 4,
                },
                {
                    "results": [
                        {"id": 21, "title": "Duplikat 21"},
                        {"id": 22, "title": "Film 22"},
                    ],
                    "total_pages": 4,
                },
            ]
        )

        items = client.fetch_catalog(movies=22, tv_shows=0)

        self.assertEqual([item.tmdb_id for item in items], list(range(1, 23)))
        self.assertEqual(client.get.call_count, 3)
        self.assertEqual(client.get.call_args_list[2].kwargs["page"], 3)

    def test_popular_catalog_stops_at_reported_last_page(self):
        client = TmdbClient(api_key="key", access_token=None)
        client.get = MagicMock(
            return_value={
                "results": [
                    {"id": 1, "title": "Jedyny film"},
                ],
                "total_pages": 1,
            }
        )

        with self.assertRaisesMessage(CommandError, "after checking 1 page"):
            client.fetch_catalog(movies=3, tv_shows=0)

        self.assertEqual(client.get.call_count, 1)

    @patch("backend.accounts.management.commands.seed_demo_data.time.sleep")
    @patch("backend.accounts.management.commands.seed_demo_data.urlopen")
    def test_retries_rate_limited_request(self, mocked_urlopen, mocked_sleep):
        rate_limit_error = HTTPError(
            "https://api.themoviedb.org/3/movie/popular",
            429,
            "Too Many Requests",
            {},
            BytesIO(b'{"status_message": "rate limited"}'),
        )
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"results": []}'
        mocked_urlopen.side_effect = [rate_limit_error, response]

        payload = TmdbClient(
            api_key="key",
            access_token=None,
            retries=2,
        ).get("/movie/popular")

        self.assertEqual(payload, {"results": []})
        self.assertEqual(mocked_urlopen.call_count, 2)
        mocked_sleep.assert_called_once_with(1)

    @patch("backend.accounts.management.commands.seed_demo_data.urlopen")
    def test_non_retryable_tmdb_error_is_reported_without_credentials(
        self,
        mocked_urlopen,
    ):
        mocked_urlopen.side_effect = HTTPError(
            "https://api.themoviedb.org/3/movie/popular",
            401,
            "Unauthorized",
            {},
            BytesIO(b'{"status_message": "invalid key"}'),
        )

        with self.assertRaisesMessage(CommandError, "TMDB request failed (401)"):
            TmdbClient(api_key="bad-key", access_token=None).get("/movie/popular")

    def test_popular_catalog_rejects_incomplete_tmdb_response(self):
        client = TmdbClient(api_key="key", access_token=None)
        client.get = MagicMock(return_value={"results": []})

        with self.assertRaisesMessage(CommandError, "returned only 0 unique movie"):
            client.fetch_catalog(movies=3, tv_shows=0)


class FullSeedCommandValidationTests(SimpleTestCase):
    def setUp(self):
        self.command = Command()

    def test_business_schema_contract_lists_every_seeded_table(self):
        expected_tables = {
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
        }

        from backend.accounts.management.commands.seed_demo_data import REQUIRED_TABLES

        self.assertEqual(REQUIRED_TABLES, expected_tables)

    @patch.object(Command, "_check_schema")
    def test_command_validates_arguments_before_contacting_tmdb(self, mocked_schema):
        invalid_options = (
            {"movies": 2, "tv_shows": 100, "users": 5, "password": "StrongPassword123!"},
            {"movies": 200, "tv_shows": -1, "users": 5, "password": "StrongPassword123!"},
            {"movies": 200, "tv_shows": 100, "users": 0, "password": "StrongPassword123!"},
            {"movies": 200, "tv_shows": 100, "users": 6, "password": "StrongPassword123!"},
            {"movies": 200, "tv_shows": 100, "users": 5, "password": None},
        )

        for options in invalid_options:
            with self.subTest(options=options):
                with self.assertRaises(CommandError):
                    self.command.handle(**options)

        mocked_schema.assert_not_called()

    @override_settings(DEBUG=False)
    def test_command_is_blocked_outside_debug_mode(self):
        with self.assertRaisesMessage(CommandError, "DEBUG=True"):
            self.command.handle(
                movies=3,
                tv_shows=0,
                users=1,
                password="StrongPassword123!",
            )

    @patch(
        "backend.accounts.management.commands.seed_demo_data.connection"
    )
    def test_schema_check_reports_missing_business_tables(self, mocked_connection):
        mocked_connection.introspection.table_names.return_value = ["content"]

        with self.assertRaisesMessage(CommandError, "agent_execution"):
            self.command._check_schema()

    @patch("backend.accounts.management.commands.seed_demo_data.transaction.atomic")
    @patch("backend.accounts.management.commands.seed_demo_data.TmdbClient")
    @patch.object(Command, "_seeded_counts", return_value={"content": 3})
    @patch.object(Command, "_seed_interactions")
    @patch.object(
        Command,
        "_seed_recommendation_history",
        return_value=([1], [(1, 1)]),
    )
    @patch.object(Command, "_seed_catalog", return_value=[1, 2, 3])
    @patch.object(Command, "_seed_users", return_value=[1])
    @patch.object(Command, "_seed_admin")
    @patch.object(Command, "_check_schema")
    @override_settings(DEBUG=True)
    def test_full_handle_orchestrates_all_seed_stages(
        self,
        mocked_schema,
        mocked_admin,
        mocked_users,
        mocked_catalog,
        mocked_history,
        mocked_interactions,
        mocked_counts,
        mocked_client_class,
        mocked_atomic,
    ):
        client = mocked_client_class.return_value
        client.fetch_genres.return_value = {18: "Dramat"}
        client.fetch_catalog.return_value = ["one", "two", "three"]
        mocked_atomic.return_value.__enter__.return_value = None
        self.command.stdout = MagicMock()

        self.command.handle(
            movies=3,
            tv_shows=0,
            users=1,
            password="StrongPassword123!",
        )

        mocked_schema.assert_called_once_with()
        mocked_client_class.assert_called_once()
        client.fetch_genres.assert_called_once_with()
        client.fetch_catalog.assert_called_once_with(movies=3, tv_shows=0)
        mocked_admin.assert_called_once_with("StrongPassword123!")
        mocked_users.assert_called_once_with("StrongPassword123!", 1)
        mocked_catalog.assert_called_once_with(
            {18: "Dramat"},
            ["one", "two", "three"],
        )
        mocked_history.assert_called_once_with([1], [1, 2, 3])
        mocked_interactions.assert_called_once_with([1], [1, 2, 3], [(1, 1)])
        mocked_counts.assert_called_once_with()

    @patch(
        "backend.accounts.management.commands.seed_demo_data.get_user_model"
    )
    def test_seed_admin_creates_idempotent_superuser(self, mocked_get_user_model):
        user_model = mocked_get_user_model.return_value
        user_model.objects.filter.return_value.first.return_value = None
        created = user_model.return_value

        result = self.command._seed_admin("StrongPassword123!")

        self.assertIs(result, created)
        self.assertEqual(created.username, "admin")
        self.assertEqual(created.email, "admin@example.com")
        self.assertTrue(created.is_active)
        self.assertTrue(created.is_staff)
        self.assertTrue(created.is_superuser)
        created.set_password.assert_called_once_with("StrongPassword123!")
        created.full_clean.assert_called_once_with()
        created.save.assert_called_once_with()

    @patch(
        "backend.accounts.management.commands.seed_demo_data.get_user_model"
    )
    def test_seed_admin_reuses_existing_account(self, mocked_get_user_model):
        existing = MagicMock()
        user_model = mocked_get_user_model.return_value
        user_model.objects.filter.return_value.first.return_value = existing

        result = self.command._seed_admin("UpdatedPassword123!")

        self.assertIs(result, existing)
        user_model.assert_not_called()
        existing.set_password.assert_called_once_with("UpdatedPassword123!")
        self.assertEqual(existing.username, "admin")
        self.assertEqual(existing.email, "admin@example.com")
        self.assertTrue(existing.is_staff)
        self.assertTrue(existing.is_superuser)
        existing.save.assert_called_once_with()
