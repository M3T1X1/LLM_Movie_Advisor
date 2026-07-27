import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection
from django.urls import reverse

from backend.test.integration.api_base import ApiIntegrationTestCase


class RegistrationApiTests(ApiIntegrationTestCase):
    def test_registration_creates_django_and_business_user_with_profile(self):
        self.client.logout()

        response = self.client.post(
            reverse("accounts:register"),
            data=json.dumps(
                {
                    "username": "registered",
                    "email": "REGISTERED@example.com",
                    "password": self.password,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["user"]["email"], "registered@example.com")
        self.assertTrue(
            get_user_model().objects.filter(username="registered").exists()
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT au.email, up.version
                FROM app_user au
                JOIN user_profile up ON up.user_id = au.id
                WHERE au.username = 'registered'
                """
            )
            self.assertEqual(cursor.fetchone(), ("registered@example.com", 1))

    @patch(
        "backend.accounts.views.sync_business_user",
        side_effect=IntegrityError("business sync failed"),
    )
    def test_registration_rolls_back_auth_user_when_business_sync_fails(
        self,
        mocked_sync,
    ):
        self.client.logout()
        response = self.client.post(
            reverse("accounts:register"),
            data=json.dumps(
                {
                    "username": "rollback-user",
                    "email": "rollback@example.com",
                    "password": self.password,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertFalse(
            get_user_model().objects.filter(username="rollback-user").exists()
        )
        self.assertNotIn("_auth_user_id", self.client.session)
        mocked_sync.assert_called_once()
