import json

from django.contrib.auth import get_user_model
from django.urls import reverse

from backend.test.integration.account_base import AccountApiTestCase


class AccountRegistrationTests(AccountApiTestCase):
    def test_registration_creates_session_and_normalizes_account_data(self):
        response = self.client.post(
            reverse("accounts:register"),
            data=json.dumps(
                {
                    "username": "new-user",
                    "email": "NEW@example.com",
                    "password": "StrongRegistrationPassword123!",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["user"]["email"], "new@example.com")
        created = get_user_model().objects.get(username="new-user")
        self.assertTrue(created.check_password("StrongRegistrationPassword123!"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), created.pk)

    def test_registration_rejects_duplicates_and_weak_passwords(self):
        duplicate_username = self.client.post(
            reverse("accounts:register"),
            data=json.dumps(
                {
                    "username": "TESTER",
                    "email": "different@example.com",
                    "password": "StrongRegistrationPassword123!",
                }
            ),
            content_type="application/json",
        )
        duplicate_email = self.client.post(
            reverse("accounts:register"),
            data=json.dumps(
                {
                    "username": "different",
                    "email": "TESTER@example.com",
                    "password": "StrongRegistrationPassword123!",
                }
            ),
            content_type="application/json",
        )
        weak_password = self.client.post(
            reverse("accounts:register"),
            data=json.dumps(
                {
                    "username": "weak-user",
                    "email": "weak@example.com",
                    "password": "password",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(duplicate_username.status_code, 409)
        self.assertEqual(duplicate_email.status_code, 409)
        self.assertEqual(weak_password.status_code, 400)
        self.assertFalse(
            get_user_model().objects.filter(username="weak-user").exists()
        )

    def test_registration_rejects_invalid_json_shapes_and_field_types(self):
        invalid_payloads = (
            "{",
            json.dumps([]),
            json.dumps(None),
            json.dumps(
                {
                    "username": 123,
                    "email": "new@example.com",
                    "password": "StrongRegistrationPassword123!",
                }
            ),
            json.dumps(
                {
                    "username": "new-user",
                    "email": None,
                    "password": "StrongRegistrationPassword123!",
                }
            ),
            json.dumps(
                {
                    "username": "   ",
                    "email": "new@example.com",
                    "password": "StrongRegistrationPassword123!",
                }
            ),
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    reverse("accounts:register"),
                    data=payload,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("detail", response.json())
        self.assertEqual(get_user_model().objects.count(), 1)
