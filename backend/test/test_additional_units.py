import os
from datetime import date
from unittest.mock import MagicMock, patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.test import RequestFactory
from django.test import SimpleTestCase, override_settings

from backend.api.admin import (
    AdminEmailAuthenticationForm,
    BusinessUserAdmin,
    ContentAdmin,
    ConversationAdmin,
    InteractionAdmin,
    SafeAuthUserAdmin,
)
from backend.accounts.services import sync_business_user
from backend.api.models import (
    AgentExecution,
    BusinessUser,
    Content,
    ContentEmbedding,
    Conversation,
    Genre,
    Interaction,
    Message,
    RecommendationRequest,
    RecommendationRun,
    RunCandidate,
    UserPreference,
    UserProfile,
)
from backend.api.views import json_object, sync_upcoming_from_tmdb
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


class ModelBehaviorTests(SimpleTestCase):
    def test_model_string_representations(self):
        self.assertEqual(
            str(BusinessUser(username="tester")),
            "tester",
        )
        self.assertEqual(
            str(Conversation(pk=7, title="Wieczorny film")),
            "Wieczorny film",
        )
        self.assertEqual(str(Conversation(pk=7)), "Rozmowa 7")

    def test_workflow_models_have_expected_default_statuses(self):
        self.assertEqual(RecommendationRun().status, "pending")
        self.assertEqual(RunCandidate().status, "pending")
        self.assertEqual(AgentExecution().status, "pending")

    def test_json_object_accepts_legacy_object_text_and_rejects_other_shapes(self):
        self.assertEqual(json_object({"source": "jsonb"}), {"source": "jsonb"})
        self.assertEqual(
            json_object('{"source": "legacy-text"}'),
            {"source": "legacy-text"},
        )
        for value in ("invalid-json", "[]", [], None, 123):
            with self.subTest(value=value):
                self.assertEqual(json_object(value), {})


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


class UpcomingSynchronizationTests(SimpleTestCase):
    @patch("backend.api.views.transaction.atomic")
    @patch("backend.api.views.SeedDemoCommand")
    @patch("backend.api.views.TmdbClient")
    def test_sync_fetches_two_polish_pages_deduplicates_and_seeds(
        self,
        mocked_client_class,
        mocked_command_class,
        mocked_atomic,
    ):
        client = mocked_client_class.return_value
        client.fetch_genres.return_value = {18: "Dramat"}
        client.get.side_effect = [
            {
                "results": [
                    {
                        "id": 1,
                        "title": "Pierwszy",
                        "release_date": "2026-08-01",
                        "genre_ids": [18],
                    },
                    {"id": 2},
                ]
            },
            {
                "results": [
                    {
                        "id": 1,
                        "title": "Pierwszy zduplikowany",
                        "release_date": "2026-08-01",
                        "genre_ids": [18],
                    },
                    {
                        "id": 3,
                        "title": "Trzeci",
                        "release_date": "2026-09-01",
                        "genre_ids": [18],
                    },
                ]
            },
        ]
        mocked_atomic.return_value.__enter__.return_value = None

        sync_upcoming_from_tmdb()

        self.assertEqual(client.get.call_count, 2)
        for page, call in enumerate(client.get.call_args_list, start=1):
            self.assertEqual(call.args, ("/movie/upcoming",))
            self.assertEqual(
                call.kwargs,
                {"language": "pl-PL", "region": "PL", "page": page},
            )
        genres, items = mocked_command_class.return_value._seed_catalog.call_args.args
        self.assertEqual(genres, {18: "Dramat"})
        self.assertEqual({item.tmdb_id for item in items}, {1, 3})
        self.assertEqual(
            next(item for item in items if item.tmdb_id == 1).title,
            "Pierwszy zduplikowany",
        )
        self.assertEqual(
            next(item for item in items if item.tmdb_id == 3).release_date,
            date(2026, 9, 1),
        )

    @patch("backend.api.views.SeedDemoCommand")
    @patch("backend.api.views.TmdbClient")
    def test_sync_does_not_seed_when_tmdb_has_no_valid_items(
        self,
        mocked_client_class,
        mocked_command_class,
    ):
        client = mocked_client_class.return_value
        client.fetch_genres.return_value = {18: "Dramat"}
        client.get.side_effect = [
            {"results": [{"id": 1}]},
            {"results": "invalid"},
        ]

        sync_upcoming_from_tmdb()

        mocked_command_class.return_value._seed_catalog.assert_not_called()


class AdminConfigurationTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get("/admin/")
        self.request.user = MagicMock()
        self.request.user.has_perm.return_value = True

    def test_all_supported_business_models_are_registered(self):
        expected_models = {
            BusinessUser,
            UserProfile,
            UserPreference,
            Conversation,
            Message,
            RecommendationRequest,
            RecommendationRun,
            Content,
            Genre,
            ContentEmbedding,
            RunCandidate,
            Interaction,
            AgentExecution,
        }

        self.assertTrue(expected_models.issubset(admin.site._registry))
        self.assertIn(get_user_model(), admin.site._registry)

    def test_admin_does_not_expose_password_fields(self):
        business_admin = BusinessUserAdmin(BusinessUser, admin.site)
        auth_admin = SafeAuthUserAdmin(get_user_model(), admin.site)

        self.assertNotIn("password", business_admin.fields)
        auth_fields = {
            field
            for _, section in auth_admin.fieldsets
            for field in section["fields"]
        }
        self.assertNotIn("password", auth_fields)
        self.assertNotIn("password", auth_admin.list_display)

    @patch("backend.api.admin.get_user_model")
    def test_admin_login_form_accepts_only_email_and_translates_it_internally(
        self,
        mocked_get_user_model,
    ):
        user = MagicMock()
        user.get_username.return_value = "admin"
        mocked_get_user_model.return_value.objects.filter.return_value.first.return_value = user
        form = AdminEmailAuthenticationForm(
            data={"username": "ADMIN@example.com", "password": "secret"}
        )

        with patch.object(
            AuthenticationForm,
            "clean",
            side_effect=lambda: form.cleaned_data,
        ):
            self.assertTrue(form.is_valid())

        self.assertEqual(form.cleaned_data["username"], "admin")
        self.assertEqual(form.fields["username"].label, "Adres e-mail")
        self.assertEqual(form.fields["username"].widget.input_type, "email")
        mocked_get_user_model.return_value.objects.filter.assert_called_once_with(
            email__iexact="ADMIN@example.com"
        )

        username_form = AdminEmailAuthenticationForm(
            data={"username": "admin", "password": "secret"}
        )
        self.assertFalse(username_form.is_valid())
        self.assertIn("username", username_form.errors)

    def test_admin_blocks_manual_creation_and_limits_deletion(self):
        model_admins = (
            BusinessUserAdmin(BusinessUser, admin.site),
            ContentAdmin(Content, admin.site),
            ConversationAdmin(Conversation, admin.site),
            InteractionAdmin(Interaction, admin.site),
        )
        for model_admin in model_admins:
            with self.subTest(model=model_admin.model):
                self.assertFalse(model_admin.has_add_permission(self.request))

        self.assertFalse(model_admins[0].has_delete_permission(self.request))
        self.assertTrue(model_admins[1].has_delete_permission(self.request))
        self.assertTrue(model_admins[2].has_delete_permission(self.request))
        self.assertTrue(model_admins[3].has_delete_permission(self.request))

    def test_content_conversation_and_interaction_fields_are_read_only(self):
        for model, admin_class in (
            (Content, ContentAdmin),
            (Conversation, ConversationAdmin),
            (Interaction, InteractionAdmin),
        ):
            with self.subTest(model=model):
                model_admin = admin_class(model, admin.site)
                self.assertEqual(
                    set(model_admin.get_readonly_fields(self.request)),
                    set(model_field.name for model_field in model._meta.get_fields()
                        if (
                            (model_field.concrete and not model_field.auto_created)
                            or model_field.many_to_many
                        )
                    ),
                )
