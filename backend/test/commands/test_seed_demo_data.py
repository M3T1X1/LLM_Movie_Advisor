from unittest.mock import MagicMock, patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from backend.accounts.management.commands.seed_demo_data import Command


class FullSeedCommandValidationTests(SimpleTestCase):
    def setUp(self):
        self.command = Command()

    def test_business_schema_contract_lists_every_seeded_table(self):
        expected_tables = {
            "app_user",
            "user_profile",
            "user_preference",
            "conversation",
            "message",
            "recommendation_request",
            "recommendation_run",
            "content",
            "genre",
            "content_genre",
            "run_candidate",
            "interaction",
            "agent_execution",
        }

        from backend.accounts.management.commands.seed_demo_data import REQUIRED_TABLES

        self.assertEqual(REQUIRED_TABLES, expected_tables)

    @patch.object(Command, "_check_schema")
    def test_command_validates_arguments_before_contacting_tmdb(self, mocked_schema):
        invalid_options = (
            {"movies": 2, "tv_shows": 100, "users": 5, "password": "StrongPassword123!"},
            {"movies": 200, "tv_shows": -1, "users": 5, "password": "StrongPassword123!"},
            {"movies": 200, "tv_shows": 100, "users": 0, "password": "StrongPassword123!"},
            {"movies": 200, "tv_shows": 100, "users": 6, "password": "StrongPassword123!"},
            {"movies": 200, "tv_shows": 100, "users": 5, "password": None},
        )

        for options in invalid_options:
            with self.subTest(options=options):
                with self.assertRaises(CommandError):
                    self.command.handle(**options)

        mocked_schema.assert_not_called()

    @override_settings(DEBUG=False)
    def test_command_is_blocked_outside_debug_mode(self):
        with self.assertRaisesMessage(CommandError, "DEBUG=True"):
            self.command.handle(
                movies=3,
                tv_shows=0,
                users=1,
                password="StrongPassword123!",
            )

    @patch(
        "backend.accounts.management.commands.seed_demo_data.connection"
    )
    def test_schema_check_reports_missing_business_tables(self, mocked_connection):
        mocked_connection.introspection.table_names.return_value = ["content"]

        with self.assertRaisesMessage(CommandError, "agent_execution"):
            self.command._check_schema()

    @patch("backend.accounts.management.commands.seed_demo_data.transaction.atomic")
    @patch("backend.accounts.management.commands.seed_demo_data.TmdbClient")
    @patch.object(Command, "_seeded_counts", return_value={"content": 3})
    @patch.object(Command, "_seed_interactions")
    @patch.object(
        Command,
        "_seed_recommendation_history",
        return_value=([1], [(1, 1)]),
    )
    @patch.object(Command, "_seed_catalog", return_value=[1, 2, 3])
    @patch.object(Command, "_seed_users", return_value=[1])
    @patch.object(Command, "_seed_admin")
    @patch.object(Command, "_check_schema")
    @override_settings(DEBUG=True)
    def test_full_handle_orchestrates_all_seed_stages(
        self,
        mocked_schema,
        mocked_admin,
        mocked_users,
        mocked_catalog,
        mocked_history,
        mocked_interactions,
        mocked_counts,
        mocked_client_class,
        mocked_atomic,
    ):
        client = mocked_client_class.return_value
        client.fetch_genres.return_value = {18: "Dramat"}
        client.fetch_catalog.return_value = ["one", "two", "three"]
        mocked_atomic.return_value.__enter__.return_value = None
        self.command.stdout = MagicMock()

        self.command.handle(
            movies=3,
            tv_shows=0,
            users=1,
            password="StrongPassword123!",
        )

        mocked_schema.assert_called_once_with()
        mocked_client_class.assert_called_once()
        client.fetch_genres.assert_called_once_with()
        client.fetch_catalog.assert_called_once_with(movies=3, tv_shows=0)
        mocked_admin.assert_called_once_with("StrongPassword123!")
        mocked_users.assert_called_once_with("StrongPassword123!", 1)
        mocked_catalog.assert_called_once_with(
            {18: "Dramat"},
            ["one", "two", "three"],
        )
        mocked_history.assert_called_once_with([1], [1, 2, 3])
        mocked_interactions.assert_called_once_with([1], [1, 2, 3], [(1, 1)])
        mocked_counts.assert_called_once_with()

    @patch(
        "backend.accounts.management.commands.seed_demo_data.get_user_model"
    )
    def test_seed_admin_creates_idempotent_superuser(self, mocked_get_user_model):
        user_model = mocked_get_user_model.return_value
        user_model.objects.filter.return_value.first.return_value = None
        created = user_model.return_value

        result = self.command._seed_admin("StrongPassword123!")

        self.assertIs(result, created)
        self.assertEqual(created.username, "admin")
        self.assertEqual(created.email, "admin@example.com")
        self.assertTrue(created.is_active)
        self.assertTrue(created.is_staff)
        self.assertTrue(created.is_superuser)
        created.set_password.assert_called_once_with("StrongPassword123!")
        created.full_clean.assert_called_once_with()
        created.save.assert_called_once_with()

    @patch(
        "backend.accounts.management.commands.seed_demo_data.get_user_model"
    )
    def test_seed_admin_reuses_existing_account(self, mocked_get_user_model):
        existing = MagicMock()
        user_model = mocked_get_user_model.return_value
        user_model.objects.filter.return_value.first.return_value = existing

        result = self.command._seed_admin("UpdatedPassword123!")

        self.assertIs(result, existing)
        user_model.assert_not_called()
        existing.set_password.assert_called_once_with("UpdatedPassword123!")
        self.assertEqual(existing.username, "admin")
        self.assertEqual(existing.email, "admin@example.com")
        self.assertTrue(existing.is_staff)
        self.assertTrue(existing.is_superuser)
        existing.save.assert_called_once_with()
