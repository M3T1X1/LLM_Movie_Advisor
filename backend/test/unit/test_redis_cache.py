from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from redis.exceptions import RedisError

from backend.redis import (
    catalog_search_cache_key,
    get_cached_catalog_search,
    get_cached_tmdb,
    invalidate_catalog_search_cache,
    set_cached_catalog_search,
    tmdb_cache_key,
)


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


class CatalogSearchCacheTests(SimpleTestCase):
    def test_catalog_key_is_stable_and_separates_query_variants(self):
        first = catalog_search_cache_key(
            {"query": "thriller", "page": 1, "sort": "rating"},
            version=3,
        )
        reordered = catalog_search_cache_key(
            {"sort": "rating", "page": 1, "query": "thriller"},
            version=3,
        )
        next_page = catalog_search_cache_key(
            {"query": "thriller", "page": 2, "sort": "rating"},
            version=3,
        )

        self.assertEqual(first, reordered)
        self.assertNotEqual(first, next_page)
        self.assertTrue(first.startswith("catalog:search:v3:"))

    @patch("backend.redis.cache")
    def test_catalog_cache_hit_returns_payload_and_reuses_resolved_key(
        self,
        mocked_cache,
    ):
        payload = {"items": [{"id": "1"}], "pagination": {}, "filters": {}}
        mocked_cache.get.side_effect = [4, payload]

        key, cached_payload = get_cached_catalog_search({"page": 1})

        self.assertEqual(
            key,
            catalog_search_cache_key({"page": 1}, version=4),
        )
        self.assertEqual(cached_payload, payload)
        set_cached_catalog_search(key, payload, timeout=300)
        mocked_cache.set.assert_called_once_with(key, payload, timeout=300)

    @patch("backend.redis.cache")
    def test_catalog_cache_failure_falls_back_without_raising(
        self,
        mocked_cache,
    ):
        mocked_cache.get.side_effect = RedisError("read unavailable")
        mocked_cache.set.side_effect = RedisError("write unavailable")

        with self.assertLogs("backend.redis", level="WARNING") as captured_logs:
            key, payload = get_cached_catalog_search({"page": 1})
            set_cached_catalog_search(key, {"items": []})

        self.assertIsNone(payload)
        self.assertIn("Catalog cache read failed", captured_logs.output[0])
        self.assertIn("Catalog cache write failed", captured_logs.output[1])

    @patch("backend.redis.cache")
    def test_catalog_invalidation_advances_version(self, mocked_cache):
        mocked_cache.add.return_value = False
        mocked_cache.incr.return_value = 8

        version = invalidate_catalog_search_cache()

        self.assertEqual(version, 8)
        mocked_cache.add.assert_called_once()
        mocked_cache.incr.assert_called_once()
