import json

from django.contrib.auth import get_user_model
from django.urls import reverse

from backend.test.integration.account_base import AccountApiTestCase


class AccountAuthenticationTests(AccountApiTestCase):
    def test_csrf_route_sets_cookie(self):
        response = self.client.get(reverse("accounts:csrf"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrftoken", response.cookies)

    def test_login_creates_session_for_valid_email_and_password(self):
        response = self.client.post(
            reverse("accounts:login"),
            data=json.dumps(
                {
                    "email": "TESTER@example.com",
                    "password": self.password,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["email"], "tester@example.com")
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_login_rejects_invalid_credentials_without_creating_session(self):
        response = self.client.post(
            reverse("accounts:login"),
            data=json.dumps(
                {
                    "email": "tester@example.com",
                    "password": "wrong-password",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_rejects_username_and_requires_email_identifier(self):
        username_payload = self.client.post(
            reverse("accounts:login"),
            data=json.dumps(
                {
                    "email": self.user.username,
                    "password": self.password,
                }
            ),
            content_type="application/json",
        )
        wrong_field_payload = self.client.post(
            reverse("accounts:login"),
            data=json.dumps(
                {
                    "username": self.user.username,
                    "password": self.password,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(username_payload.status_code, 400)
        self.assertEqual(wrong_field_payload.status_code, 400)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_email_lookup_resists_sql_injection(self):
        payloads = (
            "tester@example.com' OR '1'='1",
            "' UNION SELECT password FROM auth_user --@example.com",
            "admin@example.com'; DROP TABLE auth_user; --",
        )

        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    reverse("accounts:login"),
                    data=json.dumps(
                        {"email": payload, "password": self.password}
                    ),
                    content_type="application/json",
                )
                self.assertIn(response.status_code, (400, 401))
                self.assertNotIn("_auth_user_id", self.client.session)

        self.assertTrue(
            get_user_model().objects.filter(pk=self.user.pk).exists()
        )

    def test_login_requires_json_object_with_credentials(self):
        invalid_json = self.client.post(
            reverse("accounts:login"),
            data="{",
            content_type="application/json",
        )
        missing_password = self.client.post(
            reverse("accounts:login"),
            data=json.dumps({"email": "tester@example.com"}),
            content_type="application/json",
        )

        self.assertEqual(invalid_json.status_code, 400)
        self.assertEqual(missing_password.status_code, 400)
