import json
from unittest import SkipTest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.cache.backends.base import BaseCache
from django.test import Client, TestCase, override_settings, tag
from django.urls import reverse
from redis import Redis
from redis.exceptions import RedisError

from backend.sessions import SessionStore


REAL_REDIS_TEST_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": settings.REDIS_URL,
        "OPTIONS": {
            "socket_connect_timeout": 1,
            "socket_timeout": 1,
        },
        "KEY_PREFIX": "LLM_movie_advisor_tests",
    }
}

UNAVAILABLE_CACHE = {
    "default": {
        "BACKEND": (
            "backend.test.integration.test_redis_sessions.UnavailableCache"
        ),
        "LOCATION": "unavailable",
    }
}


class UnavailableCache(BaseCache):
    def __init__(self, location, params):
        super().__init__(params)

    def get(self, key, default=None, version=None):
        raise RedisError("Redis unavailable")

    def set(self, key, value, timeout=None, version=None):
        raise RedisError("Redis unavailable")

    def delete(self, key, version=None):
        raise RedisError("Redis unavailable")


@tag("redis")
@override_settings(CACHES=REAL_REDIS_TEST_CACHES)
class RealRedisSessionTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.redis_client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        try:
            cls.redis_client.ping()
        except RedisError as error:
            raise SkipTest("A real Redis instance is unavailable.") from error
        super().setUpClass()

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="redis-session-user",
            email="redis-session@example.com",
            password="StrongRedisSessionPassword123!",
        )

    def test_session_is_cached_in_real_redis_and_restored_from_database(self):
        client = Client()
        client.force_login(self.user)

        session_key = client.session.session_key
        session_store = SessionStore(session_key=session_key)
        cache_key = session_store.cache_key
        physical_cache_key = cache.make_key(cache_key)

        try:
            self.assertTrue(self.redis_client.exists(physical_cache_key))
            session_ttl = self.redis_client.ttl(physical_cache_key)
            self.assertGreater(session_ttl, 0)
            self.assertLessEqual(session_ttl, settings.SESSION_COOKIE_AGE)
            self.assertTrue(Session.objects.filter(pk=session_key).exists())

            cache.delete(cache_key)

            self.assertFalse(self.redis_client.exists(physical_cache_key))

            response = client.get(reverse("accounts:session"))

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["authenticated"])
            self.assertTrue(self.redis_client.exists(physical_cache_key))
        finally:
            try:
                cache.delete(cache_key)
            except RedisError:
                pass


@override_settings(CACHES=UNAVAILABLE_CACHE)
class UnavailableRedisSessionTests(TestCase):
    def setUp(self):
        self.password = "StrongRedisOutagePassword123!"
        self.user = get_user_model().objects.create_user(
            username="redis-outage-user",
            email="redis-outage@example.com",
            password=self.password,
        )

    def test_authenticated_session_uses_database_during_cache_outage(self):
        client = Client()

        with self.assertLogs(level="WARNING"):
            login_response = client.post(
                reverse("accounts:login"),
                data=json.dumps(
                    {
                        "email": self.user.email,
                        "password": self.password,
                    }
                ),
                content_type="application/json",
            )
            session_key = client.session.session_key
            session_persisted = Session.objects.filter(pk=session_key).exists()
            session_response = client.get(reverse("accounts:session"))
            logout_response = client.post(reverse("accounts:logout"))

        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(session_persisted)
        self.assertTrue(session_response.json()["authenticated"])
        self.assertEqual(
            session_response.json()["user"]["username"],
            "redis-outage-user",
        )
        self.assertEqual(logout_response.status_code, 200)
        self.assertFalse(Session.objects.filter(pk=session_key).exists())
