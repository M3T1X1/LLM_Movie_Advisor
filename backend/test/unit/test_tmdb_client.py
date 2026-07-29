import json
from datetime import date
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from backend.tmdb import TmdbClient


class TmdbClientTests(SimpleTestCase):
    def test_requires_at_least_one_authentication_method(self):
        with self.assertRaisesMessage(CommandError, "TMDB credentials are required"):
            TmdbClient(api_key=None, access_token=None)

    @patch("backend.tmdb.urlopen")
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

    @patch("backend.tmdb.urlopen")
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

    @patch("backend.tmdb.time.sleep")
    @patch("backend.tmdb.urlopen")
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

    @patch("backend.tmdb.urlopen")
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

    def test_release_catalog_fetches_movies_and_tv_with_date_filters(self):
        client = TmdbClient(api_key="key", access_token=None)
        client.get = MagicMock(
            side_effect=[
                {
                    "results": [
                        {
                            "id": 1,
                            "title": "Film pierwszy",
                            "release_date": "2026-08-01",
                        }
                    ],
                    "total_pages": 2,
                },
                {
                    "results": [
                        {
                            "id": 1,
                            "title": "Film zduplikowany",
                            "release_date": "2026-08-01",
                        },
                        {
                            "id": 2,
                            "title": "Film drugi",
                            "release_date": "2026-09-01",
                        },
                    ],
                    "total_pages": 2,
                },
                {
                    "results": [
                        {
                            "id": 1,
                            "name": "Serial pierwszy",
                            "first_air_date": "2026-08-15",
                        }
                    ],
                    "total_pages": 1,
                },
            ]
        )

        items = client.fetch_release_catalog(
            start_date=date(2026, 7, 1),
            end_date=date(2027, 7, 1),
            max_pages=3,
        )

        self.assertEqual(
            [(item.media_type, item.tmdb_id) for item in items],
            [("movie", 1), ("movie", 2), ("tv", 1)],
        )
        movie_call = client.get.call_args_list[0]
        self.assertEqual(movie_call.args, ("/discover/movie",))
        self.assertEqual(movie_call.kwargs["region"], "PL")
        self.assertEqual(movie_call.kwargs["release_date.gte"], "2026-07-01")
        self.assertEqual(movie_call.kwargs["release_date.lte"], "2027-07-01")
        tv_call = client.get.call_args_list[2]
        self.assertEqual(tv_call.args, ("/discover/tv",))
        self.assertEqual(tv_call.kwargs["first_air_date.gte"], "2026-07-01")
        self.assertEqual(tv_call.kwargs["first_air_date.lte"], "2027-07-01")

    def test_release_catalog_rejects_invalid_discover_response(self):
        client = TmdbClient(api_key="key", access_token=None)
        client.get = MagicMock(return_value={"results": "invalid"})

        with self.assertRaisesMessage(
            CommandError,
            "invalid discover movie response",
        ):
            client.fetch_release_catalog(
                start_date=date(2026, 7, 1),
                end_date=date(2026, 8, 1),
                max_pages=1,
            )

    def test_release_catalog_can_fetch_only_upcoming_movies(self):
        client = TmdbClient(api_key="key", access_token=None)
        client.get = MagicMock(
            return_value={
                "results": [
                    {
                        "id": 7,
                        "title": "Przyszły film",
                        "release_date": "2026-09-01",
                    }
                ],
                "total_pages": 1,
            }
        )

        items = client.fetch_release_catalog(
            start_date=date(2026, 8, 1),
            end_date=date(2027, 8, 1),
            max_pages=10,
            media_types=("movie",),
        )

        self.assertEqual(
            [(item.media_type, item.tmdb_id) for item in items],
            [("movie", 7)],
        )
        client.get.assert_called_once()

    def test_popular_catalog_collects_only_released_unique_items(self):
        client = TmdbClient(api_key="key", access_token=None)
        client.get = MagicMock(
            side_effect=[
                {
                    "results": [
                        {
                            "id": 1,
                            "title": "Film wydany",
                            "release_date": "2026-07-01",
                        },
                        {
                            "id": 2,
                            "title": "Film przyszły",
                            "release_date": "2026-08-01",
                        },
                    ],
                    "total_pages": 2,
                },
                {
                    "results": [
                        {
                            "id": 1,
                            "title": "Duplikat",
                            "release_date": "2026-07-01",
                        },
                        {
                            "id": 3,
                            "title": "Drugi wydany",
                            "release_date": "2026-06-01",
                        },
                    ],
                    "total_pages": 2,
                },
            ]
        )

        items = client.fetch_popular_catalog(
            media_type="movie",
            target_count=2,
            released_through=date(2026, 7, 29),
        )

        self.assertEqual([item.tmdb_id for item in items], [1, 3])
        self.assertEqual(client.get.call_count, 2)
