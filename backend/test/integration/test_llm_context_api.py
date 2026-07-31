from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

from backend.api.models import (
    BusinessUser,
    Genre,
    Interaction,
    UserPreference,
    UserProfile,
)
from backend.ollama import OllamaChatResponse
from backend.test.integration.api_base import ApiIntegrationTestCase


TEST_MIDDLEWARE = [
    middleware
    for middleware in settings.MIDDLEWARE
    if middleware != "whitenoise.middleware.WhiteNoiseMiddleware"
]


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class LlmContextApiIntegrationTests(ApiIntegrationTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    @patch("backend.api.views.get_ollama_client")
    def test_chat_grounds_model_in_postgres_context_and_reuses_redis_cache(
        self,
        mocked_get_client,
    ):
        content_id = self.insert_content(title="Mroczny Labirynt")
        genre = Genre.objects.create(tmdb_genre_id=53, name="Thriller")
        genre.contents.add(content_id)
        UserProfile.objects.filter(user_id=self.business_user_id).update(
            semantic_summary="Lubię niejednoznaczne historie bez happy endu."
        )
        UserPreference.objects.create(
            user_id=self.business_user_id,
            preference_type="genre",
            preference_value="Thriller",
            polarity=1,
            weight=0.9,
            confidence=0.8,
        )
        Interaction.objects.create(
            user_id=self.business_user_id,
            content_id=content_id,
            interaction_type="liked",
        )
        other_user = BusinessUser.objects.create(
            email="other@example.com",
            username="other-user",
        )
        UserProfile.objects.create(
            user=other_user,
            semantic_summary="PRYWATNY PROFIL INNEGO UŻYTKOWNIKA",
        )
        UserPreference.objects.create(
            user=other_user,
            preference_type="genre",
            preference_value="PRYWATNA PREFERENCJA",
            polarity=1,
        )

        ollama_client = mocked_get_client.return_value
        ollama_client.has_configured_model.return_value = True
        ollama_client.chat.return_value = OllamaChatResponse(
            content="Polecam Mroczny Labirynt.",
            model="llama3.1:8b",
            done_reason="stop",
            total_duration_ns=100,
            prompt_eval_count=50,
            eval_count=10,
        )

        first_response = self.client.post(
            reverse("api:chat"),
            data={"message": "Poleć mroczny thriller"},
            content_type="application/json",
        )
        first_messages = ollama_client.chat.call_args.args[0]
        context_message = first_messages[1]["content"]

        self.assertEqual(first_response.status_code, 200)
        self.assertIn("Mroczny Labirynt", context_message)
        self.assertIn("Thriller", context_message)
        self.assertIn("Lubię niejednoznaczne historie", context_message)
        self.assertIn('"type":"liked"', context_message)
        self.assertNotIn("PRYWATNY PROFIL", context_message)
        self.assertNotIn("PRYWATNA PREFERENCJA", context_message)
        self.assertEqual(
            first_response.json()["grounding"],
            {
                "catalogCandidateIds": [str(content_id)],
                "profileApplied": True,
                "catalogCacheHit": False,
            },
        )

        second_response = self.client.post(
            reverse("api:chat"),
            data={"message": "Poleć mroczny thriller"},
            content_type="application/json",
        )

        self.assertEqual(second_response.status_code, 200)
        self.assertTrue(second_response.json()["grounding"]["catalogCacheHit"])
