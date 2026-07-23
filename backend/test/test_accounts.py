import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse


class AuthenticationRoutesTests(TestCase):
    def setUp(self):
        self.password = "correct-horse-battery-staple"
        self.user = get_user_model().objects.create_user(
            username="tester",
            email="tester@example.com",
            password=self.password,
        )

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

    def test_session_reports_authenticated_user(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("accounts:session"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["authenticated"])
        self.assertEqual(response.json()["user"]["username"], "tester")

    def test_session_reports_anonymous_user(self):
        response = self.client.get(reverse("accounts:session"))

        self.assertEqual(
            response.json(),
            {
                "authenticated": False,
                "user": None,
            },
        )

    def test_logout_removes_session(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("accounts:logout"))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_mutating_routes_require_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)

        login_response = csrf_client.post(
            reverse("accounts:login"),
            data=json.dumps(
                {
                    "email": "tester@example.com",
                    "password": self.password,
                }
            ),
            content_type="application/json",
        )
        logout_response = csrf_client.post(reverse("accounts:logout"))
        register_response = csrf_client.post(
            reverse("accounts:register"),
            data=json.dumps(
                {
                    "username": "new-user",
                    "email": "new@example.com",
                    "password": "StrongRegistrationPassword123!",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(login_response.status_code, 403)
        self.assertEqual(logout_response.status_code, 403)
        self.assertEqual(register_response.status_code, 403)

    def test_complete_csrf_login_session_logout_flow(self):
        csrf_client = Client(enforce_csrf_checks=True)

        csrf_response = csrf_client.get(reverse("accounts:csrf"))
        initial_token = csrf_response.cookies["csrftoken"].value
        login_response = csrf_client.post(
            reverse("accounts:login"),
            data=json.dumps(
                {
                    "email": "tester@example.com",
                    "password": self.password,
                }
            ),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=initial_token,
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(
            csrf_client.get(reverse("accounts:session")).json()["authenticated"]
        )

        rotated_token = csrf_client.cookies["csrftoken"].value
        logout_response = csrf_client.post(
            reverse("accounts:logout"),
            HTTP_X_CSRFTOKEN=rotated_token,
        )

        self.assertEqual(logout_response.status_code, 200)
        self.assertFalse(
            csrf_client.get(reverse("accounts:session")).json()["authenticated"]
        )

    def test_login_rotates_session_key_without_losing_existing_session_data(self):
        session = self.client.session
        session["pre_login_marker"] = "preserved"
        session.save()
        session_key_before_login = session.session_key

        response = self.client.post(
            reverse("accounts:login"),
            data=json.dumps(
                {
                    "email": "tester@example.com",
                    "password": self.password,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(self.client.session.session_key, session_key_before_login)
        self.assertEqual(self.client.session["pre_login_marker"], "preserved")

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("accounts:login"),
            data=json.dumps(
                {
                    "email": "tester@example.com",
                    "password": self.password,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_rejects_non_object_and_invalid_credential_types(self):
        invalid_payloads = (
            [],
            None,
            "credentials",
            {"email": 123, "password": self.password},
            {"email": "tester@example.com", "password": 123},
            {"email": "   ", "password": self.password},
            {"email": "tester@example.com", "password": ""},
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    reverse("accounts:login"),
                    data=json.dumps(payload),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertNotIn("_auth_user_id", self.client.session)

    def test_authentication_responses_never_expose_password_data(self):
        login_response = self.client.post(
            reverse("accounts:login"),
            data=json.dumps(
                {
                    "email": "tester@example.com",
                    "password": self.password,
                }
            ),
            content_type="application/json",
        )
        session_response = self.client.get(reverse("accounts:session"))

        for response in (login_response, session_response):
            body = response.content.decode()
            self.assertNotIn(self.password, body)
            self.assertNotIn(self.user.password, body)
            self.assertNotIn("password", response.json().get("user", {}))

    def test_session_cookie_has_safe_browser_defaults(self):
        response = self.client.post(
            reverse("accounts:login"),
            data=json.dumps(
                {
                    "email": "tester@example.com",
                    "password": self.password,
                }
            ),
            content_type="application/json",
        )

        session_cookie = response.cookies["sessionid"]
        self.assertTrue(session_cookie["httponly"])
        self.assertEqual(session_cookie["samesite"], "Lax")

    def test_authentication_routes_reject_wrong_http_methods(self):
        cases = (
            ("get", reverse("accounts:login"), "POST"),
            ("get", reverse("accounts:register"), "POST"),
            ("post", reverse("accounts:csrf"), "GET"),
            ("post", reverse("accounts:session"), "GET"),
            ("get", reverse("accounts:logout"), "POST"),
        )

        for method, url, allowed_method in cases:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, 405)
                self.assertEqual(response.headers["Allow"], allowed_method)

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
