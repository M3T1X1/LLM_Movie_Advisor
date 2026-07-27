import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from backend.accounts.management.commands.seed_demo_data import TmdbClient


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

