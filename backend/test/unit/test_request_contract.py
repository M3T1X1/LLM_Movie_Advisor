from dataclasses import replace
from unittest.mock import MagicMock

from django.test import SimpleTestCase

from backend.recommendation_agents.explanation import ExplanationAgent
from backend.recommendation_agents.profiling import ProfilingAgent, ProfilingAgentInput
from backend.recommendation_agents.request_rules import candidate_violations
from backend.test.unit.test_recommendation_agents import candidate, profile, response
from backend.recommendation_agents.ranking import RankedCandidate, RankingAgent


def ground(text, **context):
    return ProfilingAgent._ground_output(ProfilingAgentInput(text, **context), ProfilingAgent._fallback_output(text))


class RequestContractTests(SimpleTestCase):
    def test_watched_titles_are_always_excluded_and_combined_with_conversation_exclusions(self):
        result = ground('Poleć thriller.', watched_content_ids=(1, 2))
        self.assertEqual(result.excluded_content_ids, (1, 2))
        question = ground('O czym jest ten film?', watched_content_ids=(1, 2))
        self.assertEqual(question.intent, 'content_question')
        self.assertEqual(question.excluded_content_ids, ())
        result = ground('Poleć kolejne thrillery.', watched_content_ids=(1, 2), seen_content_ids=(2, 3))
        self.assertEqual(set(result.excluded_content_ids), {1, 2, 3})
        client = MagicMock(model='test')
        client.chat.return_value = response({})
        ranked = RankingAgent(client).run('Thriller', result, (candidate(1), candidate(4)))
        self.assertNotIn(1, {item.candidate.content_id for item in ranked.selected})
        selected = (RankedCandidate(candidate(1), .9, .9, .9, 'selected', 1, ''),)
        explained = ExplanationAgent(client).run('Thriller', result, selected)
        self.assertEqual(explained.explanations, ())

    def test_quantities_belong_to_content_not_runtime_or_rating(self):
        for text, count in (
            ('Poleć dwie komedie romantyczne.', 2), ('Poleć jeden mroczny thriller.', 1),
            ('Poproszę 2 polskie komedie.', 2), ('Wybieram jeden film komediowy.', 1),
            ('Recommend two comedy TV shows with episodes under 30 minutes.', 2),
            ('Szukam filmu SF, najlepiej jednego.', 1), ('Poleć trzy dramaty do 120 minut z oceną 8.',3),
        ):
            with self.subTest(text=text):
                self.assertEqual(ground(text).result_count,count)

    def test_impossible_and_conflicting_requests_ask_instead_of_weakening(self):
        for text in ('Poleć film z oceną minimum 11 na 10.', 'Poleć pięć komedii.', 'Poleć zero filmów.',
                     'Poleć jeden film i jednocześnie trzy filmy.',
                     'Poleć film z lat 1990–1995 i z 2024 roku.',
                     'Poleć horror i nie może to być horror.', 'Poleć komedię, ale żadnej komedii.'):
            with self.subTest(text=text):
                self.assertTrue(ground(text).needs_clarification)
        self.assertEqual(ground('Poleć film z oceną minimum 11 na 10.').constraints.min_vote_average,11)

    def test_countries_languages_and_negation_are_distinct(self):
        for text,country in (('japońskie filmy','JP'),('francuskie komedie','FR'),('serial z Korei Południowej','KR'),
                             ('film z Kanady','CA'),('brytyjski dramat','GB'),('hiszpański thriller','ES')):
            with self.subTest(text=text):
                self.assertIn(country,ground('Poleć '+text).origin_countries)
        for language,code in (('angielskim','en'),('polskim','pl'),('japońskim','ja'),('francuskim','fr'),('koreańskim','ko')):
            result=ground('Poleć film w oryginalnym języku '+language)
            self.assertEqual(result.original_languages,(code,))
            self.assertEqual(result.origin_countries,())
        self.assertEqual(ground('Poleć koreański thriller bez produkcji USA.').excluded_origin_countries,('US',))

    def test_structured_continuation_keeps_filters_and_uses_ids(self):
        previous=ground('Poleć trzy komedie do 100 minut.')
        result=ground('Daj kolejne trzy z tym samym limitem czasu.',previous_profile=previous.as_dict(),seen_content_ids=(10,11,12))
        self.assertEqual(result.media_types,('movie',))
        self.assertEqual(result.genres,('Komedia',))
        self.assertEqual(result.constraints.max_runtime_minutes,100)
        self.assertFalse(result.needs_clarification)
        self.assertEqual(ground('Poleć film z roku 1500.').constraints.release_year_from,1500)
        self.assertEqual(result.excluded_content_ids,(10,11,12))

    def test_replacing_genre_drops_old_filter_and_rejecting_titles_keeps_new_genre(self):
        previous=ground('Poleć trzy filmy science fiction.')
        result=ground('Teraz zamiast science fiction chcę trzy komedie.',previous_profile=previous.as_dict())
        self.assertEqual(result.genres,('Komedia',))
        result=ground('Nie chcę tych tytułów, poleć dwa inne dramaty.')
        self.assertEqual(result.genres,('Dramat',))
        self.assertNotIn('Dramat',result.avoid)
        self.assertEqual(result.result_count,2)

    def test_natural_uncertainty_and_typos_are_not_off_topic(self):
        for text in ('Nie wiem, co obejrzeć.','Coś krótkiego.','Coś dla mnie, nie wiem na co mam ochotę.'):
            result=ground(text)
            self.assertEqual(result.intent,'recommendation')
            self.assertTrue(result.needs_clarification)
            self.assertFalse(result.avoid)
        result=ground('Chce dobry thriler do 100 minot.')
        self.assertEqual(result.genres,('Thriller',))
        self.assertEqual(result.constraints.max_runtime_minutes,100)

    def test_question_about_catalog_and_ending_is_not_new_recommendation(self):
        result=ground('Czy Interstellar jest w twoim katalogu?')
        self.assertEqual(result.intent,'content_question')
        self.assertIn('Interstellar',result.reference_titles)
        self.assertEqual(ground('Bez spoilerów: powiedz, czy na pewno kończy się szczęśliwie.').intent,'content_question')

    def test_final_gate_rejects_unknown_countries_runtime_and_wrong_genre(self):
        item=candidate(1)
        self.assertIn('excluded_country',candidate_violations(item,profile(excluded_origin_countries=('US',))))
        self.assertIn('genres',candidate_violations(item,profile(genres=('Komedia',))))
        self.assertIn('excluded_title',candidate_violations(item,profile(excluded_content_ids=(1,))))
        item=replace(item,metadata={})
        self.assertIn('max_runtime_minutes',candidate_violations(item,profile(constraints=replace(profile().constraints,max_runtime_minutes=100))))

    def test_topic_requires_evidence_in_description(self):
        for text,topic in (('Poleć film o podróżach w czasie.','podróże w czasie'),
                           ('Poleć film o sztucznej inteligencji.','sztuczna inteligencja'),
                           ('Poleć film o przyjaźni.','przyjaźń'),('Poleć film o muzyce.','muzyka')):
            result=ground(text)
            self.assertIn(topic,result.themes)
            self.assertIn('topic:'+topic,candidate_violations(candidate(1),result))


class GroundedAnswerTests(SimpleTestCase):
    def test_extra_model_claim_is_never_licensed_by_valid_quote(self):
        client=MagicMock(model='test')
        client.chat.return_value=response({'explanations':[{'content_id':1,'evidence':'Mroczna tajemnica.',
                'explanation':'To animacja o wiedźmie pochłaniającej dusze dzieci.'}]})
        selected=(RankedCandidate(candidate(1),.9,.9,.9,'selected',1,'Pasuje'),)
        result=ExplanationAgent(client).run('Thriller',profile(),selected)
        self.assertIn('Mroczna tajemnica.',result.message)
        self.assertNotIn('wiedźm',result.message)
        self.assertNotIn('animacja',result.message)

    def test_comparison_uses_previous_ids_even_with_unrelated_retrieval(self):
        previous=(candidate(1,title='Pierwszy').as_dict(),replace(candidate(2,title='Drugi'),vote_average=8.23).as_dict())
        unrelated=(replace(candidate(3,title='Obcy kandydat'),vote_average=9.9),)
        result=ExplanationAgent(MagicMock()).answer_content_question('Który z tych filmów ma najwyższą ocenę?',unrelated,
            previous_recommendations=previous)
        self.assertIn('Drugi',result.message)
        self.assertNotIn('Obcy kandydat',result.message)

    def test_ranking_cannot_select_a_mismatch_even_with_perfect_model_score(self):
        client=MagicMock(model='test')
        client.chat.return_value=response({'scores':[{'content_id':1,'relevance_score':1,'critic_score':1,'decision_reason':'Pasuje'}]})
        result=RankingAgent(client).run('Komedia',profile(genres=('Komedia',)),(candidate(1),))
        self.assertEqual(result.selected,())
