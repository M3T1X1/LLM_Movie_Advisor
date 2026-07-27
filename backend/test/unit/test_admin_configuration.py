from unittest.mock import MagicMock, patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.test import RequestFactory, SimpleTestCase

from backend.api.admin import (
    AdminEmailAuthenticationForm,
    BusinessUserAdmin,
    ContentAdmin,
    ConversationAdmin,
    InteractionAdmin,
    SafeAuthUserAdmin,
)
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
