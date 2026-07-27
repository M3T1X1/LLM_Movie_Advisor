import json

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.urls import reverse

from backend.accounts.services import sync_business_user
from backend.api.models import (
    Content,
    Conversation,
    Interaction,
    Message,
)
from backend.test.integration.api_base import ApiIntegrationTestCase


class InteractionPersistenceApiTests(ApiIntegrationTestCase):
    def test_interaction_deduplication_scope_and_event_types(self):
        first_content_id = self.insert_content(6401, "Pierwszy")
        second_content_id = self.insert_content(6402, "Drugi")
        url = reverse("api:interactions")

        watchlist_ids = []
        for content_id in (first_content_id, first_content_id, second_content_id):
            response = self.client.post(
                url,
                data=json.dumps(
                    {
                        "content_id": content_id,
                        "interaction_type": "watchlisted",
                    }
                ),
                content_type="application/json",
            )
            watchlist_ids.append(response.json()["id"])
        self.assertEqual(watchlist_ids[0], watchlist_ids[1])
        self.assertNotEqual(watchlist_ids[0], watchlist_ids[2])

        event_ids = []
        for interaction_type in ("liked", "liked", "disliked", "rated", "rated"):
            response = self.client.post(
                url,
                data=json.dumps(
                    {
                        "content_id": first_content_id,
                        "interaction_type": interaction_type,
                        "rating": 8 if interaction_type == "rated" else None,
                    }
                ),
                content_type="application/json",
            )
            event_ids.append(response.json()["id"])
        self.assertEqual(len(event_ids), len(set(event_ids)))

        missing_delete = self.client.delete(
            reverse(
                "api:interaction-detail",
                kwargs={"interaction_id": 999999},
            )
        )
        self.assertEqual(missing_delete.status_code, 404)

    def test_watchlist_deduplication_is_scoped_to_user(self):
        content_id = self.insert_content()
        first = self.client.post(
            reverse("api:interactions"),
            data=json.dumps(
                {
                    "content_id": content_id,
                    "interaction_type": "watchlisted",
                }
            ),
            content_type="application/json",
        )
        other_user = get_user_model().objects.create_user(
            username="dedup-other",
            email="dedup-other@example.com",
            password=self.password,
        )
        other_business_id = int(sync_business_user(other_user)["id"])
        other = Interaction.objects.create(
            user_id=other_business_id,
            content_id=content_id,
            interaction_type="watchlisted",
        )

        self.assertNotEqual(first.json()["id"], str(other.pk))
        self.assertEqual(
            Interaction.objects.filter(
                content_id=content_id,
                interaction_type="watchlisted",
            ).count(),
            2,
        )

    def test_deleting_candidate_sets_interaction_source_to_null(self):
        content_id = self.insert_content()
        candidate = self.create_recommendation_candidate(content_id=content_id)
        interaction = Interaction.objects.create(
            user_id=self.business_user_id,
            content_id=content_id,
            source_candidate=candidate,
            interaction_type="liked",
        )

        candidate.delete()
        interaction.refresh_from_db()

        self.assertIsNone(interaction.source_candidate_id)

    def test_database_constraints_and_delete_policies_are_enforced(self):
        content_id = self.insert_content()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Content.objects.create(
                    tmdb_id=1001,
                    media_type="movie",
                    title="Duplikat",
                )

        conversation = Conversation.objects.create(user_id=self.business_user_id)
        Message.objects.create(
            conversation=conversation,
            role="user",
            content="Pierwsza",
            sequence_no=1,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Message.objects.create(
                    conversation=conversation,
                    role="assistant",
                    content="Duplikat numeru",
                    sequence_no=1,
                )

        Interaction.objects.create(
            user_id=self.business_user_id,
            content_id=content_id,
            interaction_type="liked",
        )
        with self.assertRaises(ProtectedError):
            Content.objects.get(pk=content_id).delete()

        conversation_id = conversation.pk
        conversation.delete()
        self.assertFalse(
            Message.objects.filter(conversation_id=conversation_id).exists()
        )

    def test_user_cannot_delete_another_users_interaction(self):
        content_id = self.insert_content()
        other_user = get_user_model().objects.create_user(
            username="interaction-owner",
            email="interaction-owner@example.com",
            password=self.password,
        )
        other_business_id = int(sync_business_user(other_user)["id"])
        interaction = Interaction.objects.create(
            user_id=other_business_id,
            content_id=content_id,
            interaction_type="watchlisted",
        )

        response = self.client.delete(
            reverse(
                "api:interaction-detail",
                kwargs={"interaction_id": interaction.pk},
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Interaction.objects.filter(pk=interaction.pk).exists())
