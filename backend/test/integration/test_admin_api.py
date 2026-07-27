from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from backend.accounts.services import sync_business_user
from backend.api.models import (
    BusinessUser,
    Content,
    Conversation,
    Interaction,
    RecommendationRun,
    RunCandidate,
)
from backend.test.integration.api_base import ApiIntegrationTestCase


class AdminApiTests(ApiIntegrationTestCase):
    def test_admin_requires_staff_and_hides_passwords(self):
        anonymous = Client()
        anonymous_response = anonymous.get(reverse("admin:index"))
        self.assertEqual(anonymous_response.status_code, 302)
        self.assertIn("/admin/login/", anonymous_response.headers["Location"])

        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(self.user)

        index_response = self.client.get(reverse("admin:index"))
        business_change = self.client.get(
            reverse(
                "admin:api_businessuser_change",
                args=[self.business_user_id],
            )
        )
        auth_change = self.client.get(
            reverse("admin:auth_user_change", args=[self.user.pk])
        )

        self.assertEqual(index_response.status_code, 200)
        self.assertContains(index_response, "Baza danych platformy")
        self.assertEqual(business_change.status_code, 200)
        self.assertEqual(auth_change.status_code, 200)
        for response in (business_change, auth_change):
            with self.subTest(path=response.request["PATH_INFO"]):
                self.assertNotContains(response, 'name="password"')
                self.assertNotContains(response, "field-password")
                self.assertNotContains(response, self.user.password)

    def test_admin_can_switch_from_regular_user_by_logging_in_with_admin_email(
        self,
    ):
        admin_user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password=self.password,
        )
        self.client.force_login(self.user)

        denied_page = self.client.get(reverse("admin:index"), follow=True)
        username_login = self.client.post(
            reverse("admin:login"),
            {
                "username": "admin",
                "password": self.password,
                "next": reverse("admin:index"),
            },
        )
        self.assertContains(
            denied_page,
            "Adres e-mail",
        )
        self.assertEqual(username_login.status_code, 200)
        self.assertIn("username", username_login.context["form"].errors)
        self.assertTrue(username_login.context["form"].errors["username"])
        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            self.user.pk,
        )

        login_response = self.client.post(
            reverse("admin:login"),
            {
                "username": "ADMIN@example.com",
                "password": self.password,
                "next": reverse("admin:index"),
            },
            follow=True,
        )

        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            admin_user.pk,
        )
        self.assertContains(login_response, "Baza danych platformy")

    def test_admin_activation_action_synchronizes_auth_and_business_users(self):
        managed_user = get_user_model().objects.create_user(
            username="managed-user",
            email="managed@example.com",
            password=self.password,
            is_active=True,
        )
        managed_business_id = int(sync_business_user(managed_user)["id"])
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(self.user)
        url = reverse("admin:api_businessuser_changelist")

        deactivate = self.client.post(
            url,
            {
                "action": "deactivate_users",
                "_selected_action": [managed_business_id],
                "index": "0",
            },
            follow=True,
        )
        managed_user.refresh_from_db()
        managed_business = BusinessUser.objects.get(pk=managed_business_id)
        self.assertEqual(deactivate.status_code, 200)
        self.assertFalse(managed_user.is_active)
        self.assertFalse(managed_business.is_active)

        activate = self.client.post(
            url,
            {
                "action": "activate_users",
                "_selected_action": [managed_business_id],
                "index": "0",
            },
            follow=True,
        )
        managed_user.refresh_from_db()
        managed_business.refresh_from_db()
        self.assertEqual(activate.status_code, 200)
        self.assertTrue(managed_user.is_active)
        self.assertTrue(managed_business.is_active)

    def test_admin_allows_only_supported_deletions_and_no_manual_content_edit(self):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(self.user)
        content_id = self.insert_content(6501, "Treść panelu")
        interaction = Interaction.objects.create(
            user_id=self.business_user_id,
            content_id=content_id,
            interaction_type="liked",
        )
        conversation = Conversation.objects.create(
            user_id=self.business_user_id,
            title="Rozmowa panelu",
        )

        content_change = self.client.post(
            reverse("admin:api_content_change", args=[content_id]),
            {"title": "Niedozwolona zmiana", "_save": "Zapisz"},
        )
        self.assertIn(content_change.status_code, (200, 302))
        self.assertEqual(
            Content.objects.get(pk=content_id).title,
            "Treść panelu",
        )

        interaction_delete = self.client.post(
            reverse("admin:api_interaction_delete", args=[interaction.pk]),
            {"post": "yes"},
        )
        conversation_delete = self.client.post(
            reverse("admin:api_conversation_delete", args=[conversation.pk]),
            {"post": "yes"},
        )
        content_delete = self.client.post(
            reverse("admin:api_content_delete", args=[content_id]),
            {"post": "yes"},
        )

        self.assertEqual(interaction_delete.status_code, 302)
        self.assertEqual(conversation_delete.status_code, 302)
        self.assertEqual(content_delete.status_code, 302)
        self.assertFalse(Interaction.objects.filter(pk=interaction.pk).exists())
        self.assertFalse(Conversation.objects.filter(pk=conversation.pk).exists())
        self.assertFalse(Content.objects.filter(pk=content_id).exists())

        technical_run = self.create_recommendation_candidate(
            content_id=self.insert_content(6502, "Techniczna treść")
        ).run
        forbidden_delete = self.client.post(
            reverse("admin:api_recommendationrun_delete", args=[technical_run.pk]),
            {"post": "yes"},
        )
        self.assertEqual(forbidden_delete.status_code, 403)
        self.assertTrue(
            RecommendationRun.objects.filter(pk=technical_run.pk).exists()
        )

    def test_admin_content_deletion_removes_blocking_candidates_and_interactions(
        self,
    ):
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(self.user)
        content_id = self.insert_content(6601, "Odyseja")
        candidate = self.create_recommendation_candidate(content_id=content_id)
        run_id = candidate.run_id
        interaction = Interaction.objects.create(
            user_id=self.business_user_id,
            content_id=content_id,
            source_candidate=candidate,
            interaction_type="liked",
        )

        confirmation = self.client.get(
            reverse("admin:api_content_delete", args=[content_id])
        )
        deletion = self.client.post(
            reverse("admin:api_content_delete", args=[content_id]),
            {"post": "yes"},
        )

        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, "kandydaci rekomendacji: 1")
        self.assertContains(confirmation, "interakcje użytkowników: 1")
        self.assertEqual(deletion.status_code, 302)
        self.assertFalse(Content.objects.filter(pk=content_id).exists())
        self.assertFalse(RunCandidate.objects.filter(pk=candidate.pk).exists())
        self.assertFalse(Interaction.objects.filter(pk=interaction.pk).exists())
        self.assertTrue(RecommendationRun.objects.filter(pk=run_id).exists())
