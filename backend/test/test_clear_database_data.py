from unittest.mock import MagicMock, patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from backend.accounts.management.commands.clear_database_data import (
    BUSINESS_TABLES,
    Command,
)


@override_settings(DEBUG=True)
class ClearDatabaseDataCommandTests(SimpleTestCase):
    def setUp(self):
        self.command = Command()
        self.command.stdout = MagicMock()

    def test_cancelled_confirmation_does_not_clear_database(self):
        with (
            patch("builtins.input", return_value="nie"),
            patch.object(self.command, "_validate_schema") as validate_schema,
            patch.object(self.command, "_truncate") as truncate,
        ):
            self.command.handle(yes=False, keep_users=False)

        validate_schema.assert_not_called()
        truncate.assert_not_called()

    def test_keep_users_excludes_account_tables_but_removes_sessions(self):
        tables = self.command._target_tables(keep_users=True)

        self.assertIn("content", tables)
        self.assertIn("django_session", tables)
        self.assertNotIn("auth_user", tables)
        self.assertNotIn("app_user", tables)
        self.assertNotIn("user_profile", tables)
        self.assertNotIn("user_preference", tables)

    def test_full_clear_includes_every_business_and_account_table(self):
        tables = self.command._target_tables(keep_users=False)

        self.assertTrue(set(BUSINESS_TABLES).issubset(tables))
        self.assertIn("auth_user", tables)
        self.assertIn("django_session", tables)

    @override_settings(DEBUG=False)
    def test_command_is_blocked_outside_debug_mode(self):
        with self.assertRaisesMessage(CommandError, "only when DEBUG=True"):
            self.command.handle(yes=True, keep_users=False)
