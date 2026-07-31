from unittest.mock import patch

from django.db import DatabaseError
from django.urls import reverse
from redis.exceptions import RedisError

from backend.ollama import OllamaUnavailableError
from backend.test.integration.api_base import ApiIntegrationTestCase


class HealthApiTests(ApiIntegrationTestCase):
    def setUp(self):
        super().setUp()
        ollama_patcher = patch("backend.api.views.get_ollama_client")
        self.addCleanup(ollama_patcher.stop)
        self.mocked_get_ollama_client = ollama_patcher.start()
        self.mocked_ollama_client = (
            self.mocked_get_ollama_client.return_value
        )
        self.mocked_ollama_client.has_configured_model.return_value = True

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
                    "ollama": "ok",
                },
            },
        )
        mocked_redis_ping.assert_called_once_with()
        self.mocked_ollama_client.has_configured_model.assert_called_once_with()

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
                    "ollama": "ok",
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
                    "ollama": "ok",
                },
            },
        )
        self.assertNotIn("tajny adres Redisa", response.content.decode())
        mocked_redis_ping.assert_called_once_with()

    @patch("backend.api.views.redis_client.ping", return_value=True)
    def test_health_check_is_degraded_when_model_is_missing(
        self,
        mocked_redis_ping,
    ):
        self.mocked_ollama_client.has_configured_model.return_value = False

        response = self.client.get(reverse("api:health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "degraded",
                "services": {
                    "database": "ok",
                    "redis": "ok",
                    "ollama": "model_missing",
                },
            },
        )
        mocked_redis_ping.assert_called_once_with()

    @patch("backend.api.views.redis_client.ping", return_value=True)
    def test_health_check_sanitizes_ollama_connection_failure(
        self,
        mocked_redis_ping,
    ):
        self.mocked_ollama_client.has_configured_model.side_effect = (
            OllamaUnavailableError("tajny adres Ollamy")
        )

        response = self.client.get(reverse("api:health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "degraded",
                "services": {
                    "database": "ok",
                    "redis": "ok",
                    "ollama": "unavailable",
                },
            },
        )
        self.assertNotIn("tajny adres Ollamy", response.content.decode())
        mocked_redis_ping.assert_called_once_with()
