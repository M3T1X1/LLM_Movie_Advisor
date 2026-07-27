from unittest.mock import patch

from django.db import DatabaseError
from django.urls import reverse
from redis.exceptions import RedisError

from backend.test.integration.api_base import ApiIntegrationTestCase


class HealthApiTests(ApiIntegrationTestCase):
    @patch("backend.api.views.redis_client.ping", return_value=True)
    def test_health_check_is_public_and_checks_database(self, mocked_redis_ping):
        self.client.logout()

        response = self.client.get(reverse("api:health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "ok",
                "services": {
                    "database": "ok",
                    "redis": "ok",
                },
            },
        )
        mocked_redis_ping.assert_called_once_with()

    @patch(
        "backend.api.views.connection.ensure_connection",
        side_effect=DatabaseError("tajny adres bazy"),
    )
    @patch("backend.api.views.redis_client.ping", return_value=True)
    def test_health_check_returns_sanitized_503_when_database_is_unavailable(
        self,
        mocked_redis_ping,
        mocked_connection,
    ):
        response = self.client.get(reverse("api:health"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {
                "status": "unavailable",
                "services": {
                    "database": "unavailable",
                    "redis": "ok",
                },
            },
        )
        self.assertNotIn("tajny adres bazy", response.content.decode())
        mocked_connection.assert_called_once_with()
        mocked_redis_ping.assert_called_once_with()

    @patch(
        "backend.api.views.redis_client.ping",
        side_effect=RedisError("tajny adres Redisa"),
    )
    def test_health_check_reports_degraded_status_when_redis_is_unavailable(
        self,
        mocked_redis_ping,
    ):
        response = self.client.get(reverse("api:health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "degraded",
                "services": {
                    "database": "ok",
                    "redis": "unavailable",
                },
            },
        )
        self.assertNotIn("tajny adres Redisa", response.content.decode())
        mocked_redis_ping.assert_called_once_with()
