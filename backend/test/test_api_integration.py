import json
from pathlib import Path
from unittest import SkipTest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import TransactionTestCase, override_settings
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

    def test_health_check_is_public_and_checks_database(self):
        self.client.logout()

        response = self.client.get(reverse("api:health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_profile_update_preserves_business_identity_and_validates_email(self):
        original_business_id = self.business_user_id

        response = self.client.patch(
            reverse("api:profile"),
            data=json.dumps(
                {
                    "username": "renamed-user",
                    "email": "renamed@example.com",
                }
            ),
            content_type="application/json",
        )
        invalid_response = self.client.patch(
            reverse("api:profile"),
            data=json.dumps(
                {
                    "username": "renamed-user",
                    "email": "not-an-email",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(int(response.json()["user"]["id"]), original_business_id)
        self.assertEqual(invalid_response.status_code, 400)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, email
                FROM app_user
                WHERE id = %s
                """,
                [original_business_id],
            )
            self.assertEqual(
                cursor.fetchone(),
                (
                    original_business_id,
                    "renamed-user",
                    "renamed@example.com",
                ),
            )
            cursor.execute("SELECT COUNT(*) FROM app_user")
            self.assertEqual(cursor.fetchone()[0], 1)

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
        payload = response.json()
        content = payload["items"][0]
        self.assertEqual(content["tmdbId"], 1001)
        self.assertEqual(content["mediaType"], "movie")
        self.assertEqual(content["metadata"], {"source": "test"})
        self.assertEqual(content["genres"][0]["name"], "Thriller")
        self.assertEqual(
            payload["pagination"],
            {
                "page": 1,
                "pageSize": 20,
                "totalItems": 1,
                "totalPages": 1,
                "hasPrevious": False,
                "hasNext": False,
            },
        )
        self.assertEqual(payload["filters"]["genres"], ["Thriller"])

    def test_catalog_paginates_and_filters_the_full_database_query(self):
        content_ids = []
        for index in range(25):
            content_ids.append(
                self.insert_content(
                    tmdb_id=2000 + index,
                    title=f"Tytuł {index:02d}",
                )
            )

        page_response = self.client.get(
            reverse("api:contents"),
            {
                "page": 2,
                "page_size": 10,
                "sort": "title",
            },
        )
        filtered_response = self.client.get(
            reverse("api:contents"),
            {
                "q": "Tytuł 1",
                "media_type": "movie",
                "min_rating": "8",
                "year_from": str(timezone.now().year),
                "sort": "title",
            },
        )
        selected_response = self.client.get(
            reverse("api:contents"),
            {
                "ids": f"{content_ids[2]},{content_ids[20]}",
                "page_size": 50,
            },
        )

        self.assertEqual(page_response.status_code, 200)
        page_payload = page_response.json()
        self.assertEqual(page_payload["pagination"]["totalItems"], 25)
        self.assertEqual(page_payload["pagination"]["totalPages"], 3)
        self.assertTrue(page_payload["pagination"]["hasPrevious"])
        self.assertTrue(page_payload["pagination"]["hasNext"])
        self.assertEqual(len(page_payload["items"]), 10)
        self.assertEqual(page_payload["items"][0]["title"], "Tytuł 10")
        self.assertEqual(page_payload["items"][-1]["title"], "Tytuł 19")

        self.assertEqual(filtered_response.status_code, 200)
        filtered_payload = filtered_response.json()
        self.assertEqual(filtered_payload["pagination"]["totalItems"], 10)
        self.assertEqual(
            [item["title"] for item in filtered_payload["items"]],
            [f"Tytuł {index:02d}" for index in range(10, 20)],
        )
        self.assertEqual(selected_response.status_code, 200)
        self.assertEqual(
            {item["id"] for item in selected_response.json()["items"]},
            {str(content_ids[2]), str(content_ids[20])},
        )

    def test_catalog_rejects_invalid_pagination_and_filter_values(self):
        invalid_queries = (
            {"page": "0"},
            {"page": "abc"},
            {"page_size": "51"},
            {"sort": "random"},
            {"media_type": "documentary"},
            {"min_rating": "11"},
            {"year_from": "1800"},
            {"ids": "1,nie-liczba"},
        )

        for query in invalid_queries:
            with self.subTest(query=query):
                response = self.client.get(reverse("api:contents"), query)
                self.assertEqual(response.status_code, 400)
                self.assertIn("detail", response.json())

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
