from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from redis.exceptions import RedisError

from backend.redis import get_cached_tmdb, tmdb_cache_key


class TmdbCacheTests(SimpleTestCase):
    @patch("backend.redis.cache")
    def test_cache_hit_returns_cached_response_without_calling_tmdb(
        self,
        mocked_cache,
    ):
        client = MagicMock()
        cached_response = {"results": [{"id": 1}]}
        mocked_cache.get.return_value = cached_response
        params = {"language": "pl-PL", "region": "PL", "page": 1}
        key = tmdb_cache_key("/movie/upcoming", **params)

        result = get_cached_tmdb(client, "/movie/upcoming", **params)

        self.assertEqual(result, cached_response)
        mocked_cache.get.assert_called_once_with(key)
        mocked_cache.set.assert_not_called()
        client.get.assert_not_called()

    @patch("backend.redis.cache")
    def test_cache_miss_fetches_tmdb_and_stores_response(
        self,
        mocked_cache,
    ):
        client = MagicMock()
        tmdb_response = {"results": [{"id": 2}]}
        client.get.return_value = tmdb_response
        mocked_cache.get.return_value = None
        params = {"language": "pl-PL", "region": "PL", "page": 2}
        key = tmdb_cache_key("/movie/upcoming", **params)

        result = get_cached_tmdb(
            client,
            "/movie/upcoming",
            timeout=1800,
            **params,
        )

        self.assertEqual(result, tmdb_response)
        mocked_cache.get.assert_called_once_with(key)
        client.get.assert_called_once_with("/movie/upcoming", **params)
        mocked_cache.set.assert_called_once_with(
            key,
            tmdb_response,
            timeout=1800,
        )

    @patch("backend.redis.cache")
    def test_redis_failure_falls_back_to_tmdb_and_returns_response(
        self,
        mocked_cache,
    ):
        client = MagicMock()
        tmdb_response = {"results": [{"id": 3}]}
        client.get.return_value = tmdb_response
        mocked_cache.get.side_effect = RedisError("read unavailable")
        mocked_cache.set.side_effect = RedisError("write unavailable")
        params = {"language": "pl-PL", "region": "PL", "page": 1}

        with self.assertLogs("backend.redis", level="WARNING") as captured_logs:
            result = get_cached_tmdb(client, "/movie/upcoming", **params)

        self.assertEqual(result, tmdb_response)
        client.get.assert_called_once_with("/movie/upcoming", **params)
        self.assertEqual(mocked_cache.set.call_count, 1)
        self.assertIn("Redis cache read failed", captured_logs.output[0])
        self.assertIn("Redis cache write failed", captured_logs.output[1])

