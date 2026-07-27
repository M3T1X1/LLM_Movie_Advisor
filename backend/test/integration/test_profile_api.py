import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection
from django.urls import reverse

from backend.test.integration.api_base import ApiIntegrationTestCase


class ProfileApiTests(ApiIntegrationTestCase):
    def test_profile_update_preserves_business_identity_and_validates_email(self):
        original_business_id = self.business_user_id

        response = self.client.patch(
            reverse("api:profile"),
            data=json.dumps(
                {
                    "username": "renamed-user",
                    "email": "renamed@example.com",
                }
            ),
            content_type="application/json",
        )
        invalid_response = self.client.patch(
            reverse("api:profile"),
            data=json.dumps(
                {
                    "username": "renamed-user",
                    "email": "not-an-email",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(response.json()["user"]["id"]), original_business_id)
        self.assertEqual(invalid_response.status_code, 400)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, email
                FROM app_user
                WHERE id = %s
                """,
                [original_business_id],
            )
            self.assertEqual(
                cursor.fetchone(),
                (
                    original_business_id,
                    "renamed-user",
                    "renamed@example.com",
                ),
            )
            cursor.execute("SELECT COUNT(*) FROM app_user")
            self.assertEqual(cursor.fetchone()[0], 1)

    def test_profile_update_rejects_case_insensitive_account_conflicts(self):
        get_user_model().objects.create_user(
            username="occupied",
            email="occupied@example.com",
            password=self.password,
        )

        conflicting_username = self.client.patch(
            reverse("api:profile"),
            data=json.dumps(
                {
                    "username": "OCCUPIED",
                    "email": "new-email@example.com",
                }
            ),
            content_type="application/json",
        )
        conflicting_email = self.client.patch(
            reverse("api:profile"),
            data=json.dumps(
                {
                    "username": "new-name",
                    "email": "OCCUPIED@example.com",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(conflicting_username.status_code, 409)
        self.assertEqual(conflicting_email.status_code, 409)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "api-user")
        self.assertEqual(self.user.email, "api@example.com")

    def test_profile_update_rejects_invalid_json_and_field_types(self):
        invalid_payloads = (
            "{",
            json.dumps([]),
            json.dumps({"username": 123, "email": "valid@example.com"}),
            json.dumps({"username": "valid", "email": None}),
            json.dumps({"username": "   ", "email": "valid@example.com"}),
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.patch(
                    reverse("api:profile"),
                    data=payload,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("detail", response.json())

    @patch(
        "backend.api.views.sync_business_user",
        side_effect=IntegrityError("business sync failed"),
    )
    def test_profile_update_rolls_back_django_user_when_business_sync_fails(
        self,
        mocked_sync,
    ):
        response = self.client.patch(
            reverse("api:profile"),
            data=json.dumps(
                {
                    "username": "should-be-rolled-back",
                    "email": "rollback-profile@example.com",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "api-user")
        self.assertEqual(self.user.email, "api@example.com")
        mocked_sync.assert_called_once()
