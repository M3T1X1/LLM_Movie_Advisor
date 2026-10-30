from unittest.mock import Mock, patch

from django.test import override_settings
from django.urls import reverse

from backend.api.models import Content, ContentGenre, Conversation, Genre, UserPreference
from backend.recommendation_agents.catalog_context import resolve_catalog_references
from backend.recommendation_agents.retrieval import RetrievalAgent
from backend.test.integration.api_base import ApiIntegrationTestCase
from backend.test.integration import test_recommendation_pipeline_api as pipeline_tests
from backend.test.unit.test_request_contract import ground
from backend.test.unit.test_recommendation_agents import profile


@override_settings(LLM_SEMANTIC_SEARCH_ENABLED=False)
class CatalogContractTests(ApiIntegrationTestCase):
    def test_inflected_reference_excludes_identity_but_not_sequel(self):
        original=self.insert_content(71001,'Incepcja')
        sequel=self.insert_content(71002,'Incepcja 2')
        Content.objects.filter(pk=original).update(original_title='Inception')
        Content.objects.filter(pk=sequel).update(original_title='Inception 2')
        genre=Genre.objects.create(tmdb_genre_id=878,name='Science Fiction')
        for pk in (original,sequel):
            ContentGenre.objects.create(content_id=pk,genre=genre)
        request=resolve_catalog_references(ground('Poleć filmy podobne do Incepcji, ale bez Incepcji.'))
        self.assertEqual(request.reference_content_ids,(original,))
        self.assertIn(original,request.excluded_content_ids)
        result=RetrievalAgent(None).run('Podobne filmy',request)
        self.assertEqual([c.content_id for c in result.candidates],[sequel])

    def test_original_title_alias_excludes_polish_display_title(self):
        pk=self.insert_content(71003,'Łowca androidów')
        Content.objects.filter(pk=pk).update(original_title='Blade Runner')
        request=resolve_catalog_references(ground('Poleć coś podobnego do Blade Runnera, ale bez Blade Runnera.'))
        self.assertEqual(request.reference_content_ids,(pk,))
        self.assertIn(pk,request.excluded_content_ids)

    def test_topic_never_backfills_with_an_unrelated_popular_title(self):
        ai=self.insert_content(71004,'Świadomy robot')
        other=self.insert_content(71005,'Popularny dramat')
        Content.objects.filter(pk=ai).update(overview='Robot uzyskuje samoświadomość.')
        Content.objects.filter(pk=other).update(overview='Życie służących w latach 60.',popularity=9999)
        request=ground('Poleć trzy filmy o sztucznej inteligencji.')
        result=RetrievalAgent(None).run('Poleć trzy filmy o sztucznej inteligencji.',request)
        self.assertEqual([c.content_id for c in result.candidates],[ai])

    def test_unknown_country_cannot_prove_exclusion(self):
        korean=self.insert_content(71006,'Film koreański')
        unknown=self.insert_content(71007,'Brak kraju')
        american=self.insert_content(71008,'Film amerykański')
        Content.objects.filter(pk=korean).update(metadata={'originCountry':['KR']})
        Content.objects.filter(pk=unknown).update(metadata={})
        Content.objects.filter(pk=american).update(metadata={'originCountry':['US']})
        result=RetrievalAgent(None).run('Bez USA',profile(genres=(),themes=(),excluded_origin_countries=('US',)))
        self.assertEqual([c.content_id for c in result.candidates],[korean])

    def test_new_topic_is_grounded_in_catalog_without_a_fixed_vocabulary_entry(self):
        penguins=self.insert_content(71009,'Wyprawa')
        other=self.insert_content(71010,'Inna wyprawa')
        Content.objects.filter(pk=penguins).update(overview='Pingwiny wyruszają na daleką wyprawę.')
        Content.objects.filter(pk=other).update(overview='Kurczaki wyruszają na daleką wyprawę.')
        request=ground('Poleć film o pingwinach.')
        result=RetrievalAgent(None).run('Poleć film o pingwinach.',request)
        self.assertEqual([c.content_id for c in result.candidates],[penguins])


class ConversationIdentityTests(ApiIntegrationTestCase):
    _graph_result = pipeline_tests.RecommendationPipelineApiTests._graph_result
    _client = staticmethod(pipeline_tests.RecommendationPipelineApiTests._client)

    def setUp(self):
        super().setUp()
        self.conversation=Conversation.objects.create(user_id=self.business_user_id)
        UserPreference.objects.create(user_id=self.business_user_id,preference_type='genre',
                                      preference_value='Dramat',polarity=1)
        self.content_id=self.insert_content(title='Cichy film')

    def test_context_is_loaded_from_persisted_ids_and_is_scoped_to_conversation(self):
        states=[]
        first_id=self.content_id
        second_id=self.insert_content(71011,'Drugi film')

        def build_graph(_client,*,execution_observer):
            graph=Mock()
            def invoke(state):
                states.append(state)
                return self._graph_result()
            graph.invoke.side_effect=invoke
            return graph

        def post(conversation,prompt):
            result=self.client.post(reverse('api:conversation-recommendations',kwargs={'conversation_id':conversation.pk}),
                data={'message':prompt},content_type='application/json')
            self.assertEqual(result.status_code,201)

        with patch('backend.api.views.get_ollama_client',return_value=self._client()),patch(
            'backend.recommendation_agents.service.build_recommendation_graph',side_effect=build_graph):
            post(self.conversation,'Poleć dramat.')
            other=Conversation.objects.create(user_id=self.business_user_id)
            self.content_id=second_id
            post(other,'Poleć inny dramat.')
            self.content_id=first_id
            post(self.conversation,'Daj kolejny, bez powtórek.')
        self.assertEqual(states[1]['seen_content_ids'],())
        self.assertEqual(states[2]['seen_content_ids'],(first_id,))
        self.assertEqual([c['content_id'] for c in states[2]['previous_recommendations']],[first_id])
        self.assertEqual(states[2]['previous_profile']['genres'],['Dramat'])
