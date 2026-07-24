from unittest.mock import MagicMock, patch

from django.core.management.base import CommandError
from django.db import DatabaseError
from django.test import SimpleTestCase, override_settings

from backend.accounts.management.commands.clear_database_data import (
    BUSINESS_TABLES,
    CONFIRMATION_TEXT,
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

    def test_exact_confirmation_runs_validation_and_truncation(self):
        with (
            patch("builtins.input", return_value=f"  {CONFIRMATION_TEXT}  "),
            patch.object(self.command, "_validate_schema") as validate_schema,
            patch.object(self.command, "_truncate") as truncate,
        ):
            self.command.handle(yes=False, keep_users=False)

        expected_tables = self.command._target_tables(keep_users=False)
        validate_schema.assert_called_once_with(expected_tables)
        truncate.assert_called_once_with(expected_tables)

    def test_yes_flag_skips_prompt(self):
        with (
            patch("builtins.input") as prompt,
            patch.object(self.command, "_validate_schema"),
            patch.object(self.command, "_truncate"),
        ):
            self.command.handle(yes=True, keep_users=False)

        prompt.assert_not_called()

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

    @patch(
        "backend.accounts.management.commands.clear_database_data.connection"
    )
    def test_schema_validation_reports_every_missing_table(
        self,
        mocked_connection,
    ):
        mocked_connection.introspection.table_names.return_value = ["content"]

        with self.assertRaisesMessage(CommandError, "auth_user"):
            self.command._validate_schema(("content", "auth_user", "django_session"))

    @patch(
        "backend.accounts.management.commands.clear_database_data.connection"
    )
    @patch(
        "backend.accounts.management.commands.clear_database_data.transaction.Atomic"
    )
    def test_truncate_quotes_tables_and_restarts_identities(
        self,
        mocked_atomic,
        mocked_connection,
    ):
        mocked_atomic.return_value.__enter__.return_value = None
        mocked_connection.ops.quote_name.side_effect = lambda name: f'"{name}"'
        cursor = mocked_connection.cursor.return_value.__enter__.return_value

        self.command._truncate.__wrapped__(
            self.command,
            ("content", "django_session"),
        )

        cursor.execute.assert_called_once_with(
            'TRUNCATE TABLE "content", "django_session" RESTART IDENTITY CASCADE'
        )

    @patch(
        "backend.accounts.management.commands.clear_database_data.connection"
    )
    def test_truncate_propagates_database_failure_for_transaction_rollback(
        self,
        mocked_connection,
    ):
        mocked_connection.ops.quote_name.side_effect = lambda name: f'"{name}"'
        cursor = mocked_connection.cursor.return_value.__enter__.return_value
        cursor.execute.side_effect = DatabaseError("truncate failed")

        with self.assertRaisesMessage(DatabaseError, "truncate failed"):
            self.command._truncate.__wrapped__(self.command, ("content",))

    @override_settings(DEBUG=False)
    def test_command_is_blocked_outside_debug_mode(self):
        with self.assertRaisesMessage(CommandError, "only when DEBUG=True"):
            self.command.handle(yes=True, keep_users=False)
