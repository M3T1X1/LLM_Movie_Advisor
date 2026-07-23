import json
from pathlib import Path
from unittest import SkipTest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase
from django.urls import reverse
from django.utils import timezone


class ApplicationApiIntegrationTests(TransactionTestCase):
    reset_sequences = True
    password = "StrongIntegrationPassword123!"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        schema_path = (
            Path(settings.BASE_DIR)
            / "przydatne"
            / "postgresql_recommendation_platform_schema.sql"
        )
        if not schema_path.exists():
            raise SkipTest("Business PostgreSQL schema file is unavailable.")
        schema = schema_path.read_text(encoding="utf-8")
        with connection.cursor() as cursor:
            cursor.execute(schema)

    def setUp(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                TRUNCATE TABLE
                    agent_execution, interaction, run_candidate,
                    content_embedding, content_genre, genre, content,
                    recommendation_run, recommendation_request, message,
                    conversation, user_preference, user_profile, app_user
                RESTART IDENTITY CASCADE
                """
            )
        self.user = get_user_model().objects.create_user(
            username="api-user",
            email="api@example.com",
            password=self.password,
        )
        self.client.force_login(self.user)
        session_response = self.client.get(reverse("accounts:session"))
        self.business_user_id = int(session_response.json()["user"]["id"])

    def insert_content(self, tmdb_id=1001, title="Film integracyjny"):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO content (
                    tmdb_id, media_type, title, original_title, overview,
                    release_date, original_language, poster_path, vote_average,
                    popularity, metadata, tmdb_refreshed_at
                )
                VALUES (
                    %s, 'movie', %s, %s, 'Opis', CURRENT_DATE, 'pl',
                    '/poster.jpg', 8.2, 90.5, '{"source":"test"}'::jsonb, %s
                )
                RETURNING id
                """,
                [tmdb_id, title, title, timezone.now()],
            )
            return cursor.fetchone()[0]

    def test_registration_creates_django_and_business_user_with_profile(self):
        self.client.logout()

        response = self.client.post(
            reverse("accounts:register"),
            data=json.dumps(
                {
                    "username": "registered",
                    "email": "REGISTERED@example.com",
                    "password": self.password,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["user"]["email"], "registered@example.com")
        self.assertTrue(
            get_user_model().objects.filter(username="registered").exists()
        )
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT au.email, up.version
                FROM app_user au
                JOIN user_profile up ON up.user_id = au.id
                WHERE au.username = 'registered'
                """
            )
            self.assertEqual(cursor.fetchone(), ("registered@example.com", 1))

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

    def test_catalog_serializes_database_content_and_genres_to_camel_case(self):
        content_id = self.insert_content()
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO genre (tmdb_genre_id, name) VALUES (53, 'Thriller') RETURNING id"
            )
            genre_id = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO content_genre (content_id, genre_id) VALUES (%s, %s)",
                [content_id, genre_id],
            )

        response = self.client.get(reverse("api:contents"))

        self.assertEqual(response.status_code, 200)
        content = response.json()[0]
        self.assertEqual(content["tmdbId"], 1001)
        self.assertEqual(content["mediaType"], "movie")
        self.assertEqual(content["metadata"], {"source": "test"})
        self.assertEqual(content["genres"][0]["name"], "Thriller")

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

    def test_interaction_create_deduplicate_and_delete(self):
        content_id = self.insert_content()
        payload = {
            "content_id": str(content_id),
            "source_candidate_id": None,
            "interaction_type": "watchlisted",
            "rating": None,
            "metadata": {},
        }

        first = self.client.post(
            reverse("api:interactions"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        second = self.client.post(
            reverse("api:interactions"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["id"], second.json()["id"])
        delete_response = self.client.delete(
            reverse(
                "api:interaction-detail",
                kwargs={"interaction_id": first.json()["id"]},
            )
        )
        self.assertEqual(delete_response.status_code, 204)

    def test_resources_require_authentication(self):
        self.client.logout()
        protected_requests = (
            ("get", reverse("api:bootstrap")),
            ("get", reverse("api:contents")),
            ("get", reverse("api:conversations")),
            ("post", reverse("api:interactions")),
        )

        for method, url in protected_requests:
            with self.subTest(method=method, url=url):
                if method == "get":
                    response = self.client.get(url)
                else:
                    response = self.client.post(
                        url,
                        data="{}",
                        content_type="application/json",
                    )
                self.assertEqual(response.status_code, 401)
                self.assertEqual(
                    response.json()["detail"],
                    "Authentication required.",
                )
