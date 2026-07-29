from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from redis.exceptions import RedisError

from backend.redis import run_with_redis_lock, sync_from_tmdb


class TmdbSynchronizationLockTests(SimpleTestCase):
    @patch("backend.redis.redis_client.lock")
    def test_acquired_lock_runs_synchronization_and_releases_lock(
        self,
        mocked_lock_factory,
    ):
        lock = mocked_lock_factory.return_value
        lock.acquire.return_value = True
        operation = MagicMock()

        result = sync_from_tmdb(operation)

        self.assertTrue(result)
        mocked_lock_factory.assert_called_once_with(
            "lock:tmdb:catalog",
            timeout=120,
            blocking_timeout=5,
        )
        operation.assert_called_once_with()
        lock.acquire.assert_called_once_with(blocking=True)
        lock.release.assert_called_once_with()

    @patch("backend.redis.redis_client.lock")
    def test_busy_lock_skips_synchronization(
        self,
        mocked_lock_factory,
    ):
        lock = mocked_lock_factory.return_value
        lock.acquire.return_value = False
        operation = MagicMock()

        with self.assertLogs("backend.redis", level="WARNING"):
            result = sync_from_tmdb(operation)

        self.assertFalse(result)
        operation.assert_not_called()
        lock.release.assert_not_called()

    @patch("backend.redis.redis_client.lock")
    def test_redis_failure_runs_synchronization_without_lock(
        self,
        mocked_lock_factory,
    ):
        lock = mocked_lock_factory.return_value
        lock.acquire.side_effect = RedisError("Redis unavailable")
        operation = MagicMock()

        with self.assertLogs("backend.redis", level="WARNING"):
            result = sync_from_tmdb(operation)

        self.assertTrue(result)
        operation.assert_called_once_with()
        lock.release.assert_not_called()

    @patch("backend.redis.redis_client.lock")
    def test_generic_lock_uses_requested_key(self, mocked_lock_factory):
        lock = mocked_lock_factory.return_value
        lock.acquire.return_value = True
        operation = MagicMock()

        result = run_with_redis_lock("lock:tmdb:catalog", operation)

        self.assertTrue(result)
        mocked_lock_factory.assert_called_once_with(
            "lock:tmdb:catalog",
            timeout=120,
            blocking_timeout=5,
        )
        operation.assert_called_once_with()
