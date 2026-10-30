from unittest.mock import Mock, patch

from django.test import override_settings
from django.urls import reverse

from backend.ai_context import build_llm_application_context
from backend.api.models import BusinessUser, Conversation, Genre, Interaction, UserPreference
from backend.recommendation_agents.profiling import ProfilingAgent, build_profiling_input
from backend.recommendation_agents.retrieval import RetrievalAgent
from backend.test.integration.api_base import ApiIntegrationTestCase
from backend.test.unit.test_recommendation_agents import response


@override_settings(LLM_SEMANTIC_SEARCH_ENABLED=False, LLM_USER_INTERACTION_LIMIT=1)
class WatchedRecommendationTests(ApiIntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.business_user = BusinessUser.objects.get(pk=self.business_user_id)
        self.watched_id = self.insert_content(title='Obejrzany dramat')
        self.new_id = self.insert_content(tmdb_id=1002, title='Nowy dramat')
        genre = Genre.objects.create(tmdb_genre_id=18, name='Dramat')
        genre.contents.add(self.watched_id, self.new_id)
        UserPreference.objects.create(user=self.business_user, preference_type='genre',
                                      preference_value='Dramat', polarity=1)
        self.model = Mock(model='test-model', embedding_model='')
        self.model.list_models.return_value = ('test-model',)
        self.model.is_model_available.return_value = True
        # Exercise real profiling, retrieval, ranking and explanation fallbacks.
        self.model.chat.return_value = response({})

    def mark_watched(self, content_id):
        result = self.client.post(reverse('api:interactions'),
                                  {'content_id': content_id, 'interaction_type': 'watched'},
                                  content_type='application/json')
        self.assertEqual(result.status_code, 201)
        return result.json()['id']

    def recommend(self, conversation=None):
        conversation = conversation or Conversation.objects.create(user=self.business_user)
        with patch('backend.api.views.get_ollama_client', return_value=self.model):
            result = self.client.post(reverse('api:conversation-recommendations',
                                             kwargs={'conversation_id': conversation.pk}),
                                      {'message': 'Poleć trzy filmy Dramat.'},
                                      content_type='application/json')
        self.assertEqual(result.status_code, 201, result.content)
        return result.json()

    def selected_ids(self, payload):
        return {int(item['contentId']) for item in payload['candidates'] if item['status'] == 'selected'}

    def test_marking_watched_excludes_title_in_same_and_new_conversations(self):
        conversation = Conversation.objects.create(user=self.business_user)
        self.assertIn(self.watched_id, self.selected_ids(self.recommend(conversation)))
        self.mark_watched(self.watched_id)
        # The watched marker is older than the recent-interactions window.
        Interaction.objects.create(user=self.business_user, content_id=self.new_id,
                                   interaction_type='details_opened')
        for current in (conversation, None):
            with self.subTest(new_conversation=current is None):
                payload = self.recommend(current)
                self.assertEqual(self.selected_ids(payload), {self.new_id})
                self.assertNotIn('Obejrzany dramat', payload['assistantMessage']['content'])

    def test_watched_markers_are_user_specific_and_watchlist_is_not_watched(self):
        other = BusinessUser.objects.create(email='other@example.com', username='other')
        Interaction.objects.create(user=other, content_id=self.watched_id, interaction_type='watched')
        Interaction.objects.create(user=self.business_user, content_id=self.new_id, interaction_type='watchlisted')
        self.assertEqual(self.selected_ids(self.recommend()), {self.watched_id, self.new_id})

    def test_all_watched_returns_no_recommendations_and_unmarking_restores_eligibility(self):
        marker_id = self.mark_watched(self.watched_id)
        self.mark_watched(self.new_id)
        self.assertEqual(self.selected_ids(self.recommend()), set())
        removed = self.client.delete(reverse('api:interaction-detail', kwargs={'interaction_id': marker_id}))
        self.assertEqual(removed.status_code, 204)
        self.assertEqual(self.selected_ids(self.recommend()), {self.watched_id})

    @override_settings(LLM_SEMANTIC_SEARCH_ENABLED=True)
    def test_semantic_matches_cannot_reintroduce_watched_title(self):
        from backend.api.models import Content
        self.mark_watched(self.watched_id)
        agent_input = build_profiling_input(self.business_user, 'Poleć filmy Dramat.')
        profile = ProfilingAgent(self.model).run(agent_input).output
        matches = [Mock(content=content, similarity=.99) for content in Content.objects.all()]
        with patch('backend.recommendation_agents.retrieval.semantic_content_search', return_value=matches):
            result = RetrievalAgent(self.model).run(agent_input.current_request, profile)
        self.assertEqual({item.content_id for item in result.candidates}, {self.new_id})

    def test_stateless_catalog_cache_respects_changed_watched_markers(self):
        before = build_llm_application_context(self.user, 'Poleć filmy Dramat.', None)
        self.assertIn(self.watched_id, before.candidate_ids)
        self.mark_watched(self.watched_id)
        after = build_llm_application_context(self.user, 'Poleć filmy Dramat.', None)
        self.assertNotIn(self.watched_id, after.candidate_ids)
        self.assertIn(self.new_id, after.candidate_ids)
