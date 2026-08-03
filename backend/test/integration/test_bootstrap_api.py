from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.urls import reverse
from django.utils import timezone

from backend.accounts.services import sync_business_user
from backend.api.models import Conversation, Interaction, Message
from backend.test.integration.api_base import ApiIntegrationTestCase


class BootstrapApiTests(ApiIntegrationTestCase):
    def test_bootstrap_returns_only_current_users_relational_data(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_preference (
                    user_id, preference_type, preference_value, polarity,
                    weight, confidence
                )
                VALUES (%s, 'genre', 'Thriller', 1, 0.9, 0.8)
                """,
                [self.business_user_id],
            )
            cursor.execute(
                """
                INSERT INTO conversation (user_id, title)
                VALUES (%s, 'Rozmowa API')
                RETURNING id
                """,
                [self.business_user_id],
            )
            conversation_id = cursor.fetchone()[0]
            cursor.execute(
                """
                INSERT INTO message (conversation_id, role, content, sequence_no)
                VALUES (%s, 'user', 'Treść wiadomości', 1)
                """,
                [conversation_id],
            )

        response = self.client.get(reverse("api:bootstrap"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["user"]["username"], "api-user")
        self.assertEqual(payload["preferences"][0]["preferenceValue"], "Thriller")
        self.assertEqual(payload["conversations"][0]["title"], "Rozmowa API")
        self.assertEqual(payload["messages"][0]["content"], "Treść wiadomości")
        self.assertEqual(
            payload["preferenceOptions"]["traits"][0],
            {"preferenceType": "pacing", "label": "Szybka akcja"},
        )

    def test_bootstrap_empty_state_and_interaction_isolation(self):
        other_user = get_user_model().objects.create_user(
            username="bootstrap-other",
            email="bootstrap-other@example.com",
            password=self.password,
        )
        other_business_id = int(sync_business_user(other_user)["id"])
        content_id = self.insert_content()
        Interaction.objects.create(
            user_id=other_business_id,
            content_id=content_id,
            interaction_type="rated",
            rating=8.5,
            metadata={"private": True},
        )

        response = self.client.get(reverse("api:bootstrap"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["conversations"], [])
        self.assertEqual(payload["messages"], [])
        self.assertEqual(payload["interactions"], [])
        self.assertEqual(payload["semanticProfile"]["version"], 1)

    def test_bootstrap_supplies_default_semantic_profile_when_profile_is_missing(
        self,
    ):
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM user_profile WHERE user_id = %s",
                [self.business_user_id],
            )

        payload = self.client.get(reverse("api:bootstrap")).json()

        self.assertEqual(
            payload["semanticProfile"],
            {
                "userId": str(self.business_user_id),
                "semanticSummary": None,
                "version": 1,
                "lastRebuiltAt": None,
                "updatedAt": payload["semanticProfile"]["updatedAt"],
            },
        )

    def test_bootstrap_orders_conversations_messages_and_serializes_interaction(
        self,
    ):
        older = Conversation.objects.create(
            user_id=self.business_user_id,
            title="Starsza",
            updated_at=timezone.now() - timedelta(days=1),
        )
        newer = Conversation.objects.create(
            user_id=self.business_user_id,
            title="Nowsza",
            updated_at=timezone.now(),
        )
        Message.objects.create(
            conversation=newer,
            role="user",
            content="Druga",
            sequence_no=2,
        )
        Message.objects.create(
            conversation=newer,
            role="assistant",
            content="Pierwsza",
            sequence_no=1,
        )
        content_id = self.insert_content()
        Interaction.objects.create(
            user_id=self.business_user_id,
            content_id=content_id,
            interaction_type="rated",
            rating=8.5,
            metadata={"source": "test"},
        )

        payload = self.client.get(reverse("api:bootstrap")).json()

        self.assertEqual(
            [item["id"] for item in payload["conversations"]],
            [str(newer.pk), str(older.pk)],
        )
        self.assertEqual(
            [item["sequenceNo"] for item in payload["messages"]],
            [1, 2],
        )
        self.assertEqual(payload["interactions"][0]["rating"], 8.5)
        self.assertEqual(
            payload["interactions"][0]["metadata"],
            {"source": "test"},
        )
