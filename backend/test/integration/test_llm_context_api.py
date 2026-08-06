import json
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

from backend.api.models import (
    BusinessUser,
    ContentEmbedding,
    Genre,
    Interaction,
    UserPreference,
    UserProfile,
)
from backend.ollama import OllamaChatResponse, OllamaEmbeddingResponse
from backend.test.integration.api_base import ApiIntegrationTestCase


TEST_MIDDLEWARE = [
    middleware
    for middleware in settings.MIDDLEWARE
    if middleware != "whitenoise.middleware.WhiteNoiseMiddleware"
]


@override_settings(
    MIDDLEWARE=TEST_MIDDLEWARE,
    OLLAMA_EMBEDDING_MODEL="nomic-embed-text:latest",
    LLM_EMBEDDING_MODEL_VERSION="v1",
    LLM_EMBEDDING_SOURCE_LANGUAGE="pl-PL",
    LLM_SEMANTIC_SEARCH_ENABLED=True,
    LLM_SEMANTIC_MIN_SIMILARITY=0.2,
)
class LlmContextApiIntegrationTests(ApiIntegrationTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        UserPreference.objects.create(
            user_id=self.business_user_id,
            preference_type="format",
            preference_value="Seriale",
            polarity=1,
        )

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
        UserPreference.objects.create(
            user_id=self.business_user_id,
            preference_type="content_warning",
            preference_value="Unikanie gore",
            polarity=-1,
            weight=1.0,
            confidence=0.9,
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
        ollama_client.model = "llama3.1:8b"
        ollama_client.embedding_model = "nomic-embed-text:latest"
        ollama_client.list_models.return_value = ("llama3.1:8b",)
        ollama_client.is_model_available.side_effect = (
            lambda model, available: model in available
        )
        ollama_client.chat.return_value = OllamaChatResponse(
            content=json.dumps(
                {
                    "message": "Polecam Mroczny Labirynt.",
                    "recommendations": [
                        {
                            "content_id": content_id,
                            "explanation": "Mroczny thriller zgodny z prośbą.",
                        }
                    ],
                }
            ),
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
        recommendations = first_response.json()["recommendations"]
        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0]["rank"], 1)
        self.assertEqual(
            recommendations[0]["explanation"],
            "Mroczny thriller zgodny z prośbą.",
        )
        self.assertEqual(recommendations[0]["content"]["id"], str(content_id))
        self.assertEqual(
            recommendations[0]["content"]["title"],
            "Mroczny Labirynt",
        )
        self.assertEqual(
            recommendations[0]["content"]["genres"],
            [
                {
                    "id": str(genre.pk),
                    "tmdbGenreId": 53,
                    "name": "Thriller",
                }
            ],
        )
        self.assertIn("Mroczny Labirynt", context_message)
        self.assertIn("Thriller", context_message)
        self.assertIn("Unikanie gore", context_message)
        self.assertIn('"handling":"warning_only"', context_message)
        self.assertIn('"hard_constraint":false', context_message)
        self.assertIn(
            '"current_request_overrides_profile":true',
            context_message,
        )
        self.assertIn("Lubię niejednoznaczne historie", context_message)
        self.assertIn('"type":"liked"', context_message)
        self.assertIn(
            "Aktualna prośba użytkownika ma nad nimi pierwszeństwo",
            context_message,
        )
        self.assertIn("krótko wskaż konflikt", context_message)
        self.assertIn("Profil nigdy nie jest powodem odmowy", context_message)
        self.assertNotIn("PRYWATNY PROFIL", context_message)
        self.assertNotIn("PRYWATNA PREFERENCJA", context_message)
        self.assertEqual(
            first_response.json()["grounding"],
            {
                "catalogCandidateIds": [str(content_id)],
                "profileApplied": True,
                "catalogCacheHit": False,
                "retrievalMode": "keyword",
            },
        )

        second_response = self.client.post(
            reverse("api:chat"),
            data={"message": "Poleć mroczny thriller"},
            content_type="application/json",
        )

        self.assertEqual(second_response.status_code, 200)
        self.assertTrue(second_response.json()["grounding"]["catalogCacheHit"])

    @patch("backend.api.views.get_ollama_client")
    def test_chat_uses_pgvector_when_embedding_model_is_available(
        self,
        mocked_get_client,
    ):
        matching_id = self.insert_content(
            tmdb_id=3001,
            title="Semantycznie dopasowany film",
        )
        other_id = self.insert_content(
            tmdb_id=3002,
            title="Inny film",
        )
        matching_vector = [0.0] * 768
        matching_vector[0] = 1.0
        other_vector = [0.0] * 768
        other_vector[1] = 1.0
        for content_id, vector in (
            (matching_id, matching_vector),
            (other_id, other_vector),
        ):
            ContentEmbedding.objects.create(
                content_id=content_id,
                embedding=vector,
                embedding_model="nomic-embed-text:latest",
                model_version="v1",
                source_language="pl-PL",
                source_text_hash=str(content_id).zfill(64),
            )

        client = mocked_get_client.return_value
        client.model = "llama3.1:8b"
        client.embedding_model = "nomic-embed-text:latest"
        client.list_models.return_value = (
            "llama3.1:8b",
            "nomic-embed-text:latest",
        )
        client.is_model_available.return_value = True
        client.embed.return_value = OllamaEmbeddingResponse(
            embeddings=(tuple(matching_vector),),
            model="nomic-embed-text:latest",
            total_duration_ns=100,
            load_duration_ns=10,
            prompt_eval_count=5,
        )
        client.chat.return_value = OllamaChatResponse(
            content="Polecam Semantycznie dopasowany film.",
            model="llama3.1:8b",
            done_reason="stop",
            total_duration_ns=100,
            prompt_eval_count=50,
            eval_count=10,
        )

        response = self.client.post(
            reverse("api:chat"),
            data={"message": "Szukam podobnego klimatu"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        grounding = response.json()["grounding"]
        self.assertEqual(grounding["retrievalMode"], "semantic")
        self.assertEqual(grounding["catalogCandidateIds"][0], str(matching_id))
        context_message = client.chat.call_args.args[0][1]["content"]
        self.assertIn('"semantic_score":1.0', context_message)
