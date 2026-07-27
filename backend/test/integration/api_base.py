from pathlib import Path
from unittest import SkipTest

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from backend.api.models import (
    Conversation,
    Message,
    RecommendationRequest,
    RecommendationRun,
    RunCandidate,
)


_business_schema_initialized = False


class ApiIntegrationTestCase(TransactionTestCase):
    reset_sequences = True
    password = "StrongIntegrationPassword123!"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        global _business_schema_initialized
        if _business_schema_initialized:
            return
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
        _business_schema_initialized = True

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
