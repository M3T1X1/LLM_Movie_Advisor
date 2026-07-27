import os
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from backend.settings import env_bool, env_list


class EnvironmentSettingsTests(SimpleTestCase):
    def test_env_bool_recognizes_supported_true_and_false_values(self):
        for value in ("1", "true", "TRUE", "yes", "on"):
            with self.subTest(value=value), patch.dict(
                os.environ,
                {"TEST_BOOLEAN": value},
            ):
                self.assertTrue(env_bool("TEST_BOOLEAN"))

        for value in ("0", "false", "no", "off", "unexpected", ""):
            with self.subTest(value=value), patch.dict(
                os.environ,
                {"TEST_BOOLEAN": value},
            ):
                self.assertFalse(env_bool("TEST_BOOLEAN", True))

        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(env_bool("TEST_BOOLEAN", True))
            self.assertFalse(env_bool("TEST_BOOLEAN", False))

    def test_env_list_trims_items_and_removes_empty_values(self):
        with patch.dict(
            os.environ,
            {"TEST_LIST": " first.example.com, ,second.example.com ,, "},
        ):
            self.assertEqual(
                env_list("TEST_LIST"),
                ["first.example.com", "second.example.com"],
            )
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(env_list("TEST_LIST", "localhost, 127.0.0.1"), [
                "localhost",
                "127.0.0.1",
            ])

    @override_settings(
        DEBUG=False,
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        SECURE_SSL_REDIRECT=True,
        SECURE_HSTS_SECONDS=31536000,
    )
    def test_production_security_settings_can_be_enabled_together(self):
        from django.conf import settings

        self.assertFalse(settings.DEBUG)
        self.assertTrue(settings.SESSION_COOKIE_SECURE)
        self.assertTrue(settings.CSRF_COOKIE_SECURE)
        self.assertTrue(settings.SECURE_SSL_REDIRECT)
        self.assertGreater(settings.SECURE_HSTS_SECONDS, 0)

    def test_sessions_use_resilient_cached_database_backend(self):
        from django.conf import settings

        self.assertEqual(settings.SESSION_ENGINE, "backend.sessions")
        self.assertEqual(settings.SESSION_CACHE_ALIAS, "default")
