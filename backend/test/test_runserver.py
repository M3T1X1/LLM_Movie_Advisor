import os
import sys
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.staticfiles.management.commands.runserver import (
    Command as DjangoRunserverCommand,
)
from django.core.management.base import CommandError
from django.db import DatabaseError
from django.test import SimpleTestCase, override_settings

from backend.accounts.management.commands.runserver import Command


@override_settings(DEBUG=True)
class RunserverBootstrapTests(SimpleTestCase):
    def setUp(self):
        self.command = Command()
        self.command.stdout = MagicMock()
        self.command.stderr = MagicMock()

    @patch("backend.accounts.management.commands.runserver.call_command")
    @patch.object(Command, "_database_needs_seed", return_value=True)
    @patch.object(Command, "_run_tests")
    def test_bootstrap_runs_tests_and_seeds_empty_database(
        self,
        mocked_run_tests,
        mocked_database_needs_seed,
        mocked_call_command,
    ):
        self.command._bootstrap()

        mocked_run_tests.assert_called_once_with()
        mocked_database_needs_seed.assert_called_once_with()
        mocked_call_command.assert_called_once()
        self.assertEqual(mocked_call_command.call_args.args[0], "seed_demo_data")

    @patch("backend.accounts.management.commands.runserver.call_command")
    @patch.object(Command, "_database_needs_seed", return_value=False)
    @patch.object(Command, "_run_tests")
    def test_bootstrap_skips_seeder_when_content_exists(
        self,
        mocked_run_tests,
        mocked_database_needs_seed,
        mocked_call_command,
    ):
        self.command._bootstrap()

        mocked_run_tests.assert_called_once_with()
        mocked_database_needs_seed.assert_called_once_with()
        mocked_call_command.assert_not_called()

    @patch("backend.accounts.management.commands.runserver.subprocess.run")
    def test_failed_tests_stop_server_startup(self, mocked_run):
        mocked_run.return_value.returncode = 1

        with self.assertRaisesMessage(CommandError, "Backend tests failed"):
            self.command._run_tests()

    @patch("backend.accounts.management.commands.runserver.subprocess.run")
    def test_backend_tests_use_current_python_and_project_directory(self, mocked_run):
        mocked_run.return_value.returncode = 0

        self.command._run_tests()

        mocked_run.assert_called_once_with(
            [sys.executable, "manage.py", "test"],
            cwd=settings.BASE_DIR,
            check=False,
        )

    @patch.object(DjangoRunserverCommand, "handle", return_value="server")
    @patch.object(Command, "_bootstrap")
    def test_autoreload_child_does_not_repeat_bootstrap(
        self,
        mocked_bootstrap,
        mocked_parent_handle,
    ):
        with patch.dict(os.environ, {"RUN_MAIN": "true"}):
            result = self.command.handle(skip_bootstrap=False)

        self.assertEqual(result, "server")
        mocked_bootstrap.assert_not_called()
        mocked_parent_handle.assert_called_once()

    @patch.object(DjangoRunserverCommand, "handle", return_value="server")
    @patch.object(Command, "_bootstrap")
    def test_skip_bootstrap_option_starts_server_directly(
        self,
        mocked_bootstrap,
        mocked_parent_handle,
    ):
        with patch.dict(os.environ, {}, clear=True):
            result = self.command.handle(skip_bootstrap=True)

        self.assertEqual(result, "server")
        mocked_bootstrap.assert_not_called()
        mocked_parent_handle.assert_called_once()

    @patch("backend.accounts.management.commands.runserver.connection")
    def test_missing_business_schema_stops_startup(self, mocked_connection):
        mocked_connection.introspection.table_names.return_value = [
            "auth_user",
            "django_migrations",
        ]

        with self.assertRaisesMessage(CommandError, "business database schema is missing"):
            self.command._database_needs_seed()

    @patch("backend.accounts.management.commands.runserver.connection")
    def test_missing_django_schema_stops_startup(self, mocked_connection):
        mocked_connection.introspection.table_names.return_value = ["content"]

        with self.assertRaisesMessage(
            CommandError,
            "python manage.py migrate",
        ):
            self.command._database_needs_seed()

    @patch("backend.accounts.management.commands.runserver.Content.objects.exists")
    @patch("backend.accounts.management.commands.runserver.connection")
    def test_empty_content_table_requires_seed(self, mocked_connection, mocked_exists):
        mocked_connection.introspection.table_names.return_value = [
            "auth_user",
            "content",
            "django_migrations",
        ]
        mocked_exists.return_value = False

        self.assertTrue(self.command._database_needs_seed())
        mocked_exists.assert_called_once_with()

    @patch("backend.accounts.management.commands.runserver.Content.objects.exists")
    @patch("backend.accounts.management.commands.runserver.connection")
    def test_non_empty_content_table_skips_seed(self, mocked_connection, mocked_exists):
        mocked_connection.introspection.table_names.return_value = [
            "auth_user",
            "content",
            "django_migrations",
        ]
        mocked_exists.return_value = True

        self.assertFalse(self.command._database_needs_seed())

    @patch("backend.accounts.management.commands.runserver.connection")
    def test_database_introspection_error_is_propagated(self, mocked_connection):
        mocked_connection.introspection.table_names.side_effect = DatabaseError(
            "database unavailable"
        )

        with self.assertRaisesMessage(DatabaseError, "database unavailable"):
            self.command._database_needs_seed()

    @patch(
        "backend.accounts.management.commands.runserver.call_command",
        side_effect=CommandError("seeder failed"),
    )
    @patch.object(Command, "_database_needs_seed", return_value=True)
    @patch.object(Command, "_run_tests")
    def test_seeder_failure_stops_bootstrap(
        self,
        mocked_tests,
        mocked_needs_seed,
        mocked_call_command,
    ):
        with self.assertRaisesMessage(CommandError, "seeder failed"):
            self.command._bootstrap()

        mocked_tests.assert_called_once_with()
        mocked_needs_seed.assert_called_once_with()
        mocked_call_command.assert_called_once()

    @override_settings(DEBUG=False)
    def test_bootstrap_is_blocked_outside_debug_mode(self):
        with self.assertRaisesMessage(CommandError, "only when DEBUG=True"):
            self.command._bootstrap()
