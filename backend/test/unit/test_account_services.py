from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.accounts.services import sync_business_user


class AccountServiceFallbackTests(SimpleTestCase):
    @patch(
        "backend.accounts.services.connection.introspection.table_names",
        return_value=[],
    )
    def test_sync_business_user_falls_back_to_django_identity_without_schema(
        self,
        mocked_tables,
    ):
        user = MagicMock()
        user.pk = 42
        user.email = "fallback@example.com"
        user.get_username.return_value = "fallback"
        user.date_joined.isoformat.return_value = "2026-07-24T12:00:00+00:00"
        user.is_active = True

        result = sync_business_user(user)

        self.assertEqual(
            result,
            {
                "id": "42",
                "email": "fallback@example.com",
                "username": "fallback",
                "dateJoined": "2026-07-24T12:00:00+00:00",
                "isActive": True,
            },
        )
        mocked_tables.assert_called_once_with()

