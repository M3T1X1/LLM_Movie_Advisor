from unittest.mock import patch

from django.db import DatabaseError
from django.urls import reverse

from backend.test.integration.api_base import ApiIntegrationTestCase


class HealthApiTests(ApiIntegrationTestCase):
    def test_health_check_is_public_and_checks_database(self):
        self.client.logout()

        response = self.client.get(reverse("api:health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    @patch(
        "backend.api.views.connection.ensure_connection",
        side_effect=DatabaseError("tajny adres bazy"),
    )
    def test_health_check_returns_sanitized_503_when_database_is_unavailable(
        self,
        mocked_connection,
    ):
        response = self.client.get(reverse("api:health"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertNotIn("tajny adres bazy", response.content.decode())
        mocked_connection.assert_called_once_with()
