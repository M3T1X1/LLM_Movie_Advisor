import json
from concurrent.futures import ThreadPoolExecutor

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import Client
from django.urls import reverse

from backend.accounts.services import sync_business_user
from backend.api.models import Conversation, Message
from backend.test.integration.api_base import ApiIntegrationTestCase


class ConversationsApiTests(ApiIntegrationTestCase):
    def test_conversation_and_message_lifecycle_is_persistent(self):
        create_response = self.client.post(
            reverse("api:conversations"),
            data="{}",
            content_type="application/json",
        )
        conversation_id = create_response.json()["id"]

        message_response = self.client.post(
            reverse(
                "api:conversation-messages",
                kwargs={"conversation_id": conversation_id},
            ),
            data=json.dumps({"content": "Pierwsza trwała wiadomość"}),
            content_type="application/json",
        )
        rename_response = self.client.patch(
            reverse(
                "api:conversation-detail",
                kwargs={"conversation_id": conversation_id},
            ),
            data=json.dumps({"title": "Nowy tytuł"}),
            content_type="application/json",
        )

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(message_response.status_code, 201)
        self.assertEqual(message_response.json()["sequenceNo"], 1)
        self.assertEqual(rename_response.json()["title"], "Nowy tytuł")

        delete_response = self.client.delete(
            reverse(
                "api:conversation-detail",
                kwargs={"conversation_id": conversation_id},
            )
        )
        self.assertEqual(delete_response.status_code, 204)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM message WHERE conversation_id = %s",
                [conversation_id],
            )
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_message_length_matches_frontend_limit(self):
        conversation_response = self.client.post(
            reverse("api:conversations"),
            data="{}",
            content_type="application/json",
        )

        response = self.client.post(
            reverse(
                "api:conversation-messages",
                kwargs={"conversation_id": conversation_response.json()["id"]},
            ),
            data=json.dumps({"content": "x" * 801}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("800", response.json()["detail"])

    def test_conversation_resources_are_isolated_between_users(self):
        own_conversation = self.client.post(
            reverse("api:conversations"),
            data="{}",
            content_type="application/json",
        ).json()
        other_user = get_user_model().objects.create_user(
            username="other-user",
            email="other@example.com",
            password=self.password,
        )
        other_business_id = int(sync_business_user(other_user)["id"])
        other_conversation = Conversation.objects.create(
            user_id=other_business_id,
            title="Cudza rozmowa",
        )

        rename_response = self.client.patch(
            reverse(
                "api:conversation-detail",
                kwargs={"conversation_id": other_conversation.pk},
            ),
            data=json.dumps({"title": "Przejęta"}),
            content_type="application/json",
        )
        message_response = self.client.post(
            reverse(
                "api:conversation-messages",
                kwargs={"conversation_id": other_conversation.pk},
            ),
            data=json.dumps({"content": "Cudza wiadomość"}),
            content_type="application/json",
        )
        delete_response = self.client.delete(
            reverse(
                "api:conversation-detail",
                kwargs={"conversation_id": other_conversation.pk},
            )
        )

        self.assertEqual(rename_response.status_code, 404)
        self.assertEqual(message_response.status_code, 404)
        self.assertEqual(delete_response.status_code, 404)
        other_conversation.refresh_from_db()
        self.assertEqual(other_conversation.title, "Cudza rozmowa")
        self.assertFalse(other_conversation.messages.exists())
        self.assertTrue(
            Conversation.objects.filter(pk=own_conversation["id"]).exists()
        )

    def test_messages_are_trimmed_and_receive_consecutive_sequence_numbers(self):
        conversation_id = self.client.post(
            reverse("api:conversations"),
            data="{}",
            content_type="application/json",
        ).json()["id"]

        responses = [
            self.client.post(
                reverse(
                    "api:conversation-messages",
                    kwargs={"conversation_id": conversation_id},
                ),
                data=json.dumps({"content": f"  Wiadomość {index}  "}),
                content_type="application/json",
            )
            for index in (1, 2)
        ]
        blank_response = self.client.post(
            reverse(
                "api:conversation-messages",
                kwargs={"conversation_id": conversation_id},
            ),
            data=json.dumps({"content": "   "}),
            content_type="application/json",
        )

        self.assertEqual([item.status_code for item in responses], [201, 201])
        self.assertEqual(
            [item.json()["sequenceNo"] for item in responses],
            [1, 2],
        )
        self.assertEqual(
            [item.json()["content"] for item in responses],
            ["Wiadomość 1", "Wiadomość 2"],
        )
        self.assertEqual(blank_response.status_code, 400)

    def test_parallel_messages_receive_unique_consecutive_sequence_numbers(self):
        conversation_id = self.client.post(
            reverse("api:conversations"),
            data="{}",
            content_type="application/json",
        ).json()["id"]
        url = reverse(
            "api:conversation-messages",
            kwargs={"conversation_id": conversation_id},
        )
        clients = [Client(), Client()]
        for client in clients:
            client.force_login(self.user)

        def post_message(index):
            close_old_connections()
            try:
                return clients[index].post(
                    url,
                    data=json.dumps({"content": f"Równoległa {index}"}),
                    content_type="application/json",
                )
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(post_message, range(2)))

        self.assertEqual([response.status_code for response in responses], [201, 201])
        self.assertEqual(
            list(
                Message.objects.filter(conversation_id=conversation_id)
                .order_by("sequence_no")
                .values_list("sequence_no", flat=True)
            ),
            [1, 2],
        )

    def test_conversation_rename_validates_json_and_truncates_long_title(self):
        conversation_id = self.client.post(
            reverse("api:conversations"),
            data="{}",
            content_type="application/json",
        ).json()["id"]
        url = reverse(
            "api:conversation-detail",
            kwargs={"conversation_id": conversation_id},
        )

        invalid_json = self.client.patch(
            url,
            data="{",
            content_type="application/json",
        )
        blank_title = self.client.patch(
            url,
            data=json.dumps({"title": "   "}),
            content_type="application/json",
        )
        long_title = self.client.patch(
            url,
            data=json.dumps({"title": "x" * 300}),
            content_type="application/json",
        )

        self.assertEqual(invalid_json.status_code, 400)
        self.assertEqual(blank_title.status_code, 400)
        self.assertEqual(long_title.status_code, 200)
        self.assertEqual(len(long_title.json()["title"]), 255)

    def test_first_message_sets_title_and_timestamp_but_later_messages_keep_title(
        self,
    ):
        conversation_id = self.client.post(
            reverse("api:conversations"),
            data="{}",
            content_type="application/json",
        ).json()["id"]
        conversation = Conversation.objects.get(pk=conversation_id)
        original_updated_at = conversation.updated_at
        url = reverse(
            "api:conversation-messages",
            kwargs={"conversation_id": conversation_id},
        )

        first = self.client.post(
            url,
            data=json.dumps({"content": "  Pierwszy temat rozmowy  "}),
            content_type="application/json",
        )
        conversation.refresh_from_db()
        first_update = conversation.updated_at
        second = self.client.post(
            url,
            data=json.dumps({"content": "Inny temat"}),
            content_type="application/json",
        )
        conversation.refresh_from_db()

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(conversation.title, "Pierwszy temat rozmowy")
        self.assertGreaterEqual(first_update, original_updated_at)
        self.assertGreaterEqual(conversation.updated_at, first_update)

    def test_message_endpoint_rejects_missing_conversation_invalid_json_and_types(self):
        conversation_id = self.client.post(
            reverse("api:conversations"),
            data="{}",
            content_type="application/json",
        ).json()["id"]
        valid_url = reverse(
            "api:conversation-messages",
            kwargs={"conversation_id": conversation_id},
        )
        cases = (
            (valid_url, "{"),
            (valid_url, json.dumps([])),
            (valid_url, json.dumps({"content": 123})),
            (valid_url, json.dumps({"content": ["tekst"]})),
            (
                reverse(
                    "api:conversation-messages",
                    kwargs={"conversation_id": 999999},
                ),
                json.dumps({"content": "Wiadomość"}),
            ),
        )
        for url, payload in cases:
            with self.subTest(url=url, payload=payload):
                response = self.client.post(
                    url,
                    data=payload,
                    content_type="application/json",
                )
                self.assertIn(response.status_code, (400, 404))

        boundary = self.client.post(
            valid_url,
            data=json.dumps({"content": "x" * 800}),
            content_type="application/json",
        )
        self.assertEqual(boundary.status_code, 201)
