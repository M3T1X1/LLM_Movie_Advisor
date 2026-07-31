from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from backend.ai_context import _catalog_candidates
from backend.ollama import OllamaUnavailableError


@override_settings(
    LLM_SEMANTIC_SEARCH_ENABLED=True,
    LLM_CATALOG_CANDIDATE_LIMIT=12,
    LLM_CATALOG_OVERVIEW_MAX_LENGTH=600,
    LLM_CATALOG_CONTEXT_CACHE_TIMEOUT=300,
    LLM_CATALOG_SEARCH_TERM_LIMIT=10,
    OLLAMA_EMBEDDING_MODEL="nomic-embed-text:latest",
    LLM_EMBEDDING_MODEL_VERSION="v1",
    LLM_EMBEDDING_SOURCE_LANGUAGE="pl-PL",
    LLM_SEMANTIC_MIN_SIMILARITY=0.2,
)
class AiCatalogContextTests(SimpleTestCase):
    @patch("backend.ai_context.set_cached_llm_catalog_context")
    @patch(
        "backend.ai_context._query_catalog_candidates",
        return_value=[{"id": 7, "title": "Fallback"}],
    )
    @patch(
        "backend.ai_context.semantic_content_search",
        side_effect=OllamaUnavailableError("unavailable"),
    )
    @patch(
        "backend.ai_context.get_cached_llm_catalog_context",
        return_value=("cache-key", None),
    )
    def test_semantic_failure_falls_back_to_keyword_candidates(
        self,
        mocked_cache_get,
        mocked_semantic_search,
        mocked_keyword_search,
        mocked_cache_set,
    ):
        client = MagicMock()
        candidates, cache_hit, mode = _catalog_candidates(
            "mroczny thriller",
            ["zagadki"],
            client,
        )

        self.assertEqual(candidates, [{"id": 7, "title": "Fallback"}])
        self.assertFalse(cache_hit)
        self.assertEqual(mode, "keyword_fallback")
        mocked_semantic_search.assert_called_once_with(
            "mroczny thriller",
            [],
            limit=12,
            client=client,
        )
        mocked_keyword_search.assert_called_once()
        cached_payload = mocked_cache_set.call_args.args[1]
        self.assertEqual(cached_payload["retrieval_mode"], "keyword_fallback")

    @patch("backend.ai_context.set_cached_llm_catalog_context")
    @patch("backend.ai_context.semantic_content_search")
    @patch("backend.ai_context._query_catalog_candidates")
    @patch(
        "backend.ai_context.get_cached_llm_catalog_context",
        return_value=(
            "cache-key",
            {
                "candidates": [{"id": 9, "title": "Z Redis"}],
                "retrieval_mode": "semantic",
            },
        ),
    )
    def test_valid_cached_context_skips_ollama_and_database(
        self,
        mocked_cache_get,
        mocked_keyword_search,
        mocked_semantic_search,
        mocked_cache_set,
    ):
        candidates, cache_hit, mode = _catalog_candidates(
            "science fiction",
            [],
            MagicMock(),
        )

        self.assertEqual(candidates, [{"id": 9, "title": "Z Redis"}])
        self.assertTrue(cache_hit)
        self.assertEqual(mode, "semantic")
        mocked_semantic_search.assert_not_called()
        mocked_keyword_search.assert_not_called()
        mocked_cache_set.assert_not_called()

    @patch("backend.ai_context.set_cached_llm_catalog_context")
    @patch(
        "backend.ai_context._query_catalog_candidates",
        return_value=[{"id": 8, "title": "Profilowy wybór"}],
    )
    @patch("backend.ai_context.semantic_content_search", return_value=[])
    @patch(
        "backend.ai_context.get_cached_llm_catalog_context",
        return_value=("cache-key", None),
    )
    def test_vague_request_can_use_positive_profile_hints(
        self,
        mocked_cache_get,
        mocked_semantic_search,
        mocked_keyword_search,
        mocked_cache_set,
    ):
        client = MagicMock()

        _catalog_candidates("Poleć coś", ["Science Fiction"], client)

        mocked_semantic_search.assert_called_once_with(
            "Poleć coś",
            ["Science Fiction"],
            limit=12,
            client=client,
        )
