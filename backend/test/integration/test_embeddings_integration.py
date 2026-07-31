from unittest.mock import MagicMock

from django.conf import settings
from django.test import override_settings

from backend.api.models import ContentEmbedding, Genre
from backend.embeddings import semantic_content_search, sync_content_embeddings
from backend.ollama import OllamaEmbeddingResponse
from backend.test.integration.api_base import ApiIntegrationTestCase


TEST_MIDDLEWARE = [
    middleware
    for middleware in settings.MIDDLEWARE
    if middleware != "whitenoise.middleware.WhiteNoiseMiddleware"
]


def embedding_response(*embeddings):
    return OllamaEmbeddingResponse(
        embeddings=tuple(tuple(vector) for vector in embeddings),
        model="nomic-embed-text:latest",
        total_duration_ns=100,
        load_duration_ns=10,
        prompt_eval_count=20,
    )


@override_settings(
    MIDDLEWARE=TEST_MIDDLEWARE,
    OLLAMA_EMBEDDING_MODEL="nomic-embed-text:latest",
    LLM_EMBEDDING_MODEL_VERSION="v1",
    LLM_EMBEDDING_SOURCE_LANGUAGE="pl-PL",
    LLM_EMBEDDING_BATCH_SIZE=8,
    LLM_SEMANTIC_MIN_SIMILARITY=0.2,
)
class EmbeddingIntegrationTests(ApiIntegrationTestCase):
    def test_sync_creates_embedding_and_skips_unchanged_source(self):
        content_id = self.insert_content(title="Kosmiczna zagadka")
        genre = Genre.objects.create(tmdb_genre_id=878, name="Science Fiction")
        genre.contents.add(content_id)
        client = MagicMock()
        vector = [0.0] * 768
        vector[0] = 1.0
        client.embed.return_value = embedding_response(vector)

        first = sync_content_embeddings(
            content_ids=[content_id],
            client=client,
        )
        second = sync_content_embeddings(
            content_ids=[content_id],
            client=client,
        )

        self.assertEqual(first.generated, 1)
        self.assertEqual(first.created, 1)
        self.assertEqual(second.skipped, 1)
        self.assertEqual(client.embed.call_count, 1)
        record = ContentEmbedding.objects.get(content_id=content_id)
        self.assertEqual(record.embedding_model, "nomic-embed-text:latest")
        self.assertEqual(record.model_version, "v1")
        self.assertEqual(len(record.embedding), 768)
        source_text = client.embed.call_args.args[0][0]
        self.assertTrue(source_text.startswith("search_document: "))
        self.assertIn("Kosmiczna zagadka", source_text)
        self.assertIn("Science Fiction", source_text)

    def test_semantic_search_orders_content_by_cosine_similarity(self):
        matching_id = self.insert_content(
            tmdb_id=2001,
            title="Wyprawa kosmiczna",
        )
        other_id = self.insert_content(
            tmdb_id=2002,
            title="Romans historyczny",
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
        client = MagicMock()
        client.embed.return_value = embedding_response(matching_vector)

        matches = semantic_content_search(
            "ambitne science fiction",
            [],
            limit=5,
            client=client,
        )

        self.assertEqual([item.content.pk for item in matches], [matching_id])
        self.assertAlmostEqual(matches[0].similarity, 1.0)
        query_text = client.embed.call_args.args[0][0]
        self.assertTrue(query_text.startswith("search_query: "))

