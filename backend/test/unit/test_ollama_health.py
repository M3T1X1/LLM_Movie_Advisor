import json
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from backend.api.views import health
from backend.ollama import OllamaUnavailableError


class OllamaHealthViewTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get("/api/health/")

    @patch("backend.api.views.connection.ensure_connection")
    @patch("backend.api.views.redis_client.ping", return_value=True)
    @patch("backend.api.views.get_ollama_client")
    def test_reports_configured_model_as_healthy(
        self,
        mocked_get_client,
        mocked_redis_ping,
        mocked_connection,
    ):
        mocked_get_client.return_value.missing_configured_models.return_value = ()

        response = health(self.request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content),
            {
                "status": "ok",
                "services": {
                    "database": "ok",
                    "redis": "ok",
                    "ollama": "ok",
                },
            },
        )
        mocked_connection.assert_called_once_with()
        mocked_redis_ping.assert_called_once_with()

    @patch("backend.api.views.connection.ensure_connection")
    @patch("backend.api.views.redis_client.ping", return_value=True)
    @patch("backend.api.views.get_ollama_client")
    def test_reports_missing_model_as_degraded(
        self,
        mocked_get_client,
        mocked_redis_ping,
        mocked_connection,
    ):
        mocked_get_client.return_value.missing_configured_models.return_value = (
            "nomic-embed-text:latest",
        )

        response = health(self.request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content),
            {
                "status": "degraded",
                "services": {
                    "database": "ok",
                    "redis": "ok",
                    "ollama": "model_missing",
                },
            },
        )

    @patch("backend.api.views.connection.ensure_connection")
    @patch("backend.api.views.redis_client.ping", return_value=True)
    @patch("backend.api.views.get_ollama_client")
    def test_reports_unavailable_ollama_without_exposing_details(
        self,
        mocked_get_client,
        mocked_redis_ping,
        mocked_connection,
    ):
        mocked_get_client.return_value.missing_configured_models.side_effect = (
            OllamaUnavailableError("tajny adres")
        )

        response = health(self.request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content),
            {
                "status": "degraded",
                "services": {
                    "database": "ok",
                    "redis": "ok",
                    "ollama": "unavailable",
                },
            },
        )
        self.assertNotIn("tajny adres", response.content.decode())
