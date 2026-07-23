import json

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase
from django.test import override_settings
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

        self.assertEqual(login_response.status_code, 403)
        self.assertEqual(logout_response.status_code, 403)


@override_settings(DEBUG=True)
class SeedDataCommandTests(TestCase):
    def test_seed_data_creates_user_with_hashed_password(self):
        call_command(
            "seed_data",
            username="demo",
            email="demo@example.com",
            password="StrongDemoPassword123!",
            verbosity=0,
        )

        user = get_user_model().objects.get(username="demo")
        self.assertEqual(user.email, "demo@example.com")
        self.assertTrue(user.check_password("StrongDemoPassword123!"))
        self.assertNotEqual(user.password, "StrongDemoPassword123!")

    def test_seed_data_is_idempotent_and_updates_existing_user(self):
        call_command(
            "seed_data",
            username="demo",
            email="first@example.com",
            password="FirstDemoPassword123!",
            verbosity=0,
        )
        call_command(
            "seed_data",
            username="demo",
            email="second@example.com",
            password="SecondDemoPassword123!",
            verbosity=0,
        )

        self.assertEqual(get_user_model().objects.filter(username="demo").count(), 1)
        user = get_user_model().objects.get(username="demo")
        self.assertEqual(user.email, "second@example.com")
        self.assertTrue(user.check_password("SecondDemoPassword123!"))

    @override_settings(DEBUG=False)
    def test_seed_data_is_blocked_outside_debug_mode(self):
        with self.assertRaisesMessage(
            CommandError,
            "Seed data can only be loaded when DEBUG=True.",
        ):
            call_command(
                "seed_data",
                username="demo",
                email="demo@example.com",
                password="StrongDemoPassword123!",
                verbosity=0,
            )
