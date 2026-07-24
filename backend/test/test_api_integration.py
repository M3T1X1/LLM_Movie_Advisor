import json
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from unittest import SkipTest
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.core.management import call_command
from django.db import DatabaseError, connection
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from backend.accounts.management.commands.seed_demo_data import (
    Command as SeedDemoCommand,
)
from backend.accounts.management.commands.seed_demo_data import TmdbCatalogItem
from backend.accounts.services import sync_business_user
from backend.api.models import (
    Content,
    ContentGenre,
    Conversation,
    Genre,
    Interaction,
    Message,
    RecommendationRequest,
    RecommendationRun,
    RunCandidate,
)


class ApplicationApiIntegrationTests(TransactionTestCase):
    reset_sequences = True
    password = "StrongIntegrationPassword123!"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        schema_path = (
            Path(settings.BASE_DIR)
            / "backend"
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

    def create_recommendation_candidate(
        self,
        *,
        user_id=None,
        content_id=None,
        created_at=None,
    ):
        user_id = user_id or self.business_user_id
        content_id = content_id or self.insert_content()
        conversation = Conversation.objects.create(user_id=user_id)
        message = Message.objects.create(
            conversation=conversation,
            role="user",
            content="Poleć mi film",
            sequence_no=1,
        )
        recommendation_request = RecommendationRequest.objects.create(
            conversation=conversation,
            trigger_message=message,
        )
        run = RecommendationRun.objects.create(
            request=recommendation_request,
            status="completed",
        )
        candidate = RunCandidate.objects.create(
            run=run,
            content_id=content_id,
            status="selected",
        )
        if created_at is not None:
            RunCandidate.objects.filter(pk=candidate.pk).update(
                created_at=created_at
            )
            candidate.refresh_from_db()
        return candidate

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

    @patch(
        "backend.api.views.connection.ensure_connection",
        side_effect=DatabaseError("tajny adres bazy"),
    )
    def test_health_check_returns_sanitized_503_when_database_is_unavailable(
        self,
        mocked_connection,
    ):
        response = self.client.get(reverse("api:health"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertNotIn("tajny adres bazy", response.content.decode())
        mocked_connection.assert_called_once_with()

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

    def test_profile_update_rejects_case_insensitive_account_conflicts(self):
        get_user_model().objects.create_user(
            username="occupied",
            email="occupied@example.com",
            password=self.password,
        )

        conflicting_username = self.client.patch(
            reverse("api:profile"),
            data=json.dumps(
                {
                    "username": "OCCUPIED",
                    "email": "new-email@example.com",
                }
            ),
            content_type="application/json",
        )
        conflicting_email = self.client.patch(
            reverse("api:profile"),
            data=json.dumps(
                {
                    "username": "new-name",
                    "email": "OCCUPIED@example.com",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(conflicting_username.status_code, 409)
        self.assertEqual(conflicting_email.status_code, 409)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "api-user")
        self.assertEqual(self.user.email, "api@example.com")

    def test_profile_update_rejects_invalid_json_and_field_types(self):
        invalid_payloads = (
            "{",
            json.dumps([]),
            json.dumps({"username": 123, "email": "valid@example.com"}),
            json.dumps({"username": "valid", "email": None}),
            json.dumps({"username": "   ", "email": "valid@example.com"}),
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.patch(
                    reverse("api:profile"),
                    data=payload,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("detail", response.json())

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

    def test_orm_seeder_upserts_catalog_and_relations_idempotently(self):
        item = TmdbCatalogItem(
            tmdb_id=9001,
            media_type="movie",
            title="Film ORM",
            original_title="ORM Movie",
            overview="Opis",
            release_date=date(2026, 1, 2),
            original_language="pl",
            poster_path="/orm.jpg",
            vote_average=8.5,
            popularity=100.0,
            genre_ids=(18, 53),
            metadata={"source": "test"},
        )
        command = SeedDemoCommand()

        catalog = [
            item,
            replace(item, tmdb_id=9002, title="Drugi film ORM"),
            replace(item, tmdb_id=9003, title="Trzeci film ORM"),
        ]
        first_ids = command._seed_catalog(
            {18: "Dramat", 53: "Thriller"},
            catalog,
        )
        second_ids = command._seed_catalog(
            {18: "Dramat", 53: "Thriller"},
            [replace(item, title="Film ORM po aktualizacji"), *catalog[1:]],
        )

        self.assertEqual(first_ids, second_ids)
        content = Content.objects.get(pk=first_ids[0])
        self.assertEqual(content.title, "Film ORM po aktualizacji")
        self.assertEqual(
            set(content.genres.values_list("name", flat=True)),
            {"Dramat", "Thriller"},
        )
        self.assertEqual(Genre.objects.count(), 2)
        conversation_ids, candidates = command._seed_recommendation_history(
            [self.business_user_id],
            first_ids,
        )
        command._seed_interactions(
            [self.business_user_id],
            first_ids,
            candidates,
        )
        self.assertEqual(len(conversation_ids), 5)
        self.assertEqual(len(candidates), 12)
        self.assertEqual(Interaction.objects.count(), 30)

    def test_orm_seeder_normalizes_composite_tv_genres(self):
        item = TmdbCatalogItem(
            tmdb_id=9100,
            media_type="tv",
            title="Serial ze złożonymi gatunkami",
            original_title="Composite Genres",
            overview="Opis",
            release_date=date(2026, 2, 3),
            original_language="en",
            poster_path="/genres.jpg",
            vote_average=7.5,
            popularity=80.0,
            genre_ids=(10759, 10765, 10768),
            metadata={"source": "test"},
        )

        content_id = SeedDemoCommand()._seed_catalog(
            {
                10759: "Akcja i Przygoda",
                10765: "Sci-Fi i Fantasy",
                10768: "War & Politics",
            },
            [item],
        )[0]

        self.assertEqual(
            set(
                Content.objects.get(pk=content_id).genres.values_list(
                    "name",
                    flat=True,
                )
            ),
            {
                "Akcja",
                "Przygodowy",
                "Science Fiction",
                "Fantasy",
                "Wojenny",
                "Polityczny",
            },
        )
        self.assertFalse(
            Genre.objects.filter(tmdb_genre_id__in=(10759, 10765)).exists()
        )

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

    @patch("backend.api.views.sync_upcoming_from_tmdb")
    def test_upcoming_uses_fresh_cache_without_contacting_tmdb(self, mocked_sync):
        content_id = self.insert_content(title="Świeża premiera")
        Content.objects.filter(pk=content_id).update(
            release_date=date.today() + timedelta(days=7),
            tmdb_refreshed_at=timezone.now(),
        )

        response = self.client.get(reverse("api:upcoming-contents"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["title"] for item in response.json()],
            ["Świeża premiera"],
        )
        mocked_sync.assert_not_called()

    @patch("backend.api.views.sync_upcoming_from_tmdb")
    def test_upcoming_syncs_stale_cache_and_refresh_forces_sync(self, mocked_sync):
        content_id = self.insert_content(title="Nieaktualna premiera")
        Content.objects.filter(pk=content_id).update(
            release_date=date.today() + timedelta(days=7),
            tmdb_refreshed_at=timezone.now() - timedelta(days=2),
        )

        stale_response = self.client.get(reverse("api:upcoming-contents"))
        refresh_response = self.client.get(
            reverse("api:upcoming-contents"),
            {"refresh": "1"},
        )

        self.assertEqual(stale_response.status_code, 200)
        self.assertEqual(refresh_response.status_code, 200)
        self.assertEqual(mocked_sync.call_count, 2)

    @patch(
        "backend.api.views.sync_upcoming_from_tmdb",
        side_effect=CommandError("TMDB unavailable"),
    )
    def test_upcoming_falls_back_to_cache_unless_refresh_was_requested(
        self,
        mocked_sync,
    ):
        content_id = self.insert_content(title="Premiera z cache")
        Content.objects.filter(pk=content_id).update(
            release_date=date.today() + timedelta(days=7),
            tmdb_refreshed_at=timezone.now() - timedelta(days=2),
        )

        cached_response = self.client.get(reverse("api:upcoming-contents"))
        refresh_response = self.client.get(
            reverse("api:upcoming-contents"),
            {"refresh": "1"},
        )

        self.assertEqual(cached_response.status_code, 200)
        self.assertEqual(cached_response.json()[0]["title"], "Premiera z cache")
        self.assertEqual(refresh_response.status_code, 503)
        self.assertEqual(
            refresh_response.json(),
            {"detail": "TMDB upcoming releases are unavailable."},
        )
        self.assertEqual(mocked_sync.call_count, 2)

    @patch("backend.api.views.sync_upcoming_from_tmdb")
    def test_upcoming_returns_only_future_movies_in_expected_order(
        self,
        mocked_sync,
    ):
        first_id = self.insert_content(2001, "Pierwsza")
        popular_id = self.insert_content(2002, "Popularniejsza tego samego dnia")
        less_popular_id = self.insert_content(2003, "Mniej popularna tego samego dnia")
        past_id = self.insert_content(2004, "Film archiwalny")
        tv_id = self.insert_content(2005, "Przyszły serial")
        fresh_at = timezone.now()
        Content.objects.filter(pk=first_id).update(
            release_date=date.today() + timedelta(days=1),
            popularity=10,
            tmdb_refreshed_at=fresh_at,
        )
        Content.objects.filter(pk=popular_id).update(
            release_date=date.today() + timedelta(days=2),
            popularity=90,
            tmdb_refreshed_at=fresh_at,
        )
        Content.objects.filter(pk=less_popular_id).update(
            release_date=date.today() + timedelta(days=2),
            popularity=20,
            tmdb_refreshed_at=fresh_at,
        )
        Content.objects.filter(pk=past_id).update(
            release_date=date.today() - timedelta(days=1),
            tmdb_refreshed_at=fresh_at,
        )
        Content.objects.filter(pk=tv_id).update(
            media_type="tv",
            release_date=date.today() + timedelta(days=1),
            tmdb_refreshed_at=fresh_at,
        )

        response = self.client.get(reverse("api:upcoming-contents"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["title"] for item in response.json()],
            [
                "Pierwsza",
                "Popularniejsza tego samego dnia",
                "Mniej popularna tego samego dnia",
            ],
        )
        mocked_sync.assert_not_called()

    def test_recommendation_trends_reject_invalid_period_and_support_empty_result(
        self,
    ):
        invalid_response = self.client.get(
            reverse("api:trends"),
            {"period": "year"},
        )
        empty_response = self.client.get(
            reverse("api:trends"),
            {"period": "day"},
        )

        self.assertEqual(invalid_response.status_code, 400)
        self.assertIn("detail", invalid_response.json())
        self.assertEqual(empty_response.status_code, 200)
        self.assertEqual(empty_response.json()["totalRecommendations"], 0)
        self.assertEqual(empty_response.json()["genreTrends"], [])
        self.assertEqual(empty_response.json()["contentTrends"], [])

    def test_recommendation_trends_exclude_candidates_outside_selected_period(
        self,
    ):
        recent_content_id = self.insert_content(3001, "Najnowszy kandydat")
        old_content_id = self.insert_content(3002, "Stary kandydat")
        self.create_recommendation_candidate(
            content_id=recent_content_id,
            created_at=timezone.now() - timedelta(hours=12),
        )
        self.create_recommendation_candidate(
            content_id=old_content_id,
            created_at=timezone.now() - timedelta(days=2),
        )

        day_response = self.client.get(
            reverse("api:trends"),
            {"period": "day"},
        )
        week_response = self.client.get(
            reverse("api:trends"),
            {"period": "week"},
        )

        self.assertEqual(day_response.json()["totalRecommendations"], 1)
        self.assertEqual(
            day_response.json()["contentTrends"][0]["content"]["title"],
            "Najnowszy kandydat",
        )
        self.assertEqual(week_response.json()["totalRecommendations"], 2)

    def test_recommendation_trends_limit_and_order_genres_and_contents(self):
        genres = [
            Genre.objects.create(tmdb_genre_id=4000 + index, name=f"Gatunek {index}")
            for index in range(6)
        ]
        for content_index in range(4):
            content_id = self.insert_content(
                5000 + content_index,
                f"Trend {content_index}",
            )
            for genre in genres[: 6 - content_index]:
                ContentGenre.objects.create(
                    content_id=content_id,
                    genre=genre,
                )
            for _ in range(4 - content_index):
                self.create_recommendation_candidate(content_id=content_id)

        response = self.client.get(
            reverse("api:trends"),
            {"period": "month"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["totalRecommendations"], 10)
        self.assertEqual(len(payload["genreTrends"]), 5)
        self.assertEqual(len(payload["contentTrends"]), 3)
        self.assertEqual(
            [item["recommendationCount"] for item in payload["genreTrends"]],
            sorted(
                [
                    item["recommendationCount"]
                    for item in payload["genreTrends"]
                ],
                reverse=True,
            ),
        )
        self.assertEqual(
            [item["recommendationCount"] for item in payload["contentTrends"]],
            [4, 3, 2],
        )

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

    def test_interactions_validate_identifiers_type_rating_and_metadata(self):
        content_id = self.insert_content()
        invalid_payloads = (
            {
                "content_id": 999999,
                "interaction_type": "liked",
            },
            {
                "content_id": content_id,
                "source_candidate_id": 999999,
                "interaction_type": "liked",
            },
            {
                "content_id": content_id,
                "interaction_type": "shared",
            },
            {
                "content_id": content_id,
                "interaction_type": "rated",
                "rating": -1,
            },
            {
                "content_id": content_id,
                "interaction_type": "rated",
                "rating": 11,
            },
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    reverse("api:interactions"),
                    data=json.dumps(payload),
                    content_type="application/json",
                )
                self.assertIn(response.status_code, (400, 404))
                self.assertIn("detail", response.json())

        metadata_response = self.client.post(
            reverse("api:interactions"),
            data=json.dumps(
                {
                    "content_id": content_id,
                    "interaction_type": "liked",
                    "rating": 9,
                    "metadata": ["not", "an", "object"],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(metadata_response.status_code, 201)
        self.assertIsNone(metadata_response.json()["rating"])
        self.assertEqual(metadata_response.json()["metadata"], {})

    def test_rated_interaction_rejects_boolean_rating(self):
        content_id = self.insert_content()

        response = self.client.post(
            reverse("api:interactions"),
            data=json.dumps(
                {
                    "content_id": content_id,
                    "interaction_type": "rated",
                    "rating": True,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())

    def test_source_candidate_must_belong_to_current_user(self):
        content_id = self.insert_content()
        other_user = get_user_model().objects.create_user(
            username="candidate-owner",
            email="candidate-owner@example.com",
            password=self.password,
        )
        other_business_id = int(sync_business_user(other_user)["id"])
        candidate = self.create_recommendation_candidate(
            user_id=other_business_id,
            content_id=content_id,
        )

        response = self.client.post(
            reverse("api:interactions"),
            data=json.dumps(
                {
                    "content_id": content_id,
                    "source_candidate_id": candidate.pk,
                    "interaction_type": "liked",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("detail", response.json())
        self.assertFalse(
            Interaction.objects.filter(
                user_id=self.business_user_id,
                source_candidate=candidate,
            ).exists()
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
