from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import override_settings

from backend.test.integration.api_base import ApiIntegrationTestCase


class ClearDatabaseDataIntegrationTests(ApiIntegrationTestCase):
    @override_settings(DEBUG=True)
    def test_clear_database_data_removes_rows_but_preserves_schema(self):
        self.insert_content()

        call_command(
            "clear_database_data",
            yes=True,
            keep_users=False,
            verbosity=0,
        )

        self.assertEqual(get_user_model().objects.count(), 0)
        with connection.cursor() as cursor:
            for table in ("app_user", "user_profile", "content"):
                cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                self.assertEqual(cursor.fetchone()[0], 0)
            self.assertIn("content", connection.introspection.table_names())

    @override_settings(DEBUG=True)
    def test_clear_database_data_can_keep_accounts_and_profiles(self):
        self.insert_content()

        call_command(
            "clear_database_data",
            yes=True,
            keep_users=True,
            verbosity=0,
        )

        self.assertTrue(
            get_user_model().objects.filter(username="api-user").exists()
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM app_user WHERE id = %s",
                [self.business_user_id],
            )
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute(
                "SELECT COUNT(*) FROM user_profile WHERE user_id = %s",
                [self.business_user_id],
            )
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute("SELECT COUNT(*) FROM content")
            self.assertEqual(cursor.fetchone()[0], 0)
