from unittest.mock import MagicMock
from django.test import SimpleTestCase
from backend.ollama import OllamaUnavailableError
from backend.recommendation_agents.explanation import ExplanationAgent
from backend.recommendation_agents.ranking import RankedCandidate
from backend.test.unit.test_recommendation_agents import candidate, profile, response


class LlmExplanationTests(SimpleTestCase):
    def test_match_reason_preserves_request_reason_and_adds_mood_without_synopsis(self):
        result = ExplanationAgent.recommendation_reason((), mood='wesoły')
        self.assertEqual(result, 'Ten tytuł wybrano na podstawie kryteriów Twojej prośby. Szukany nastrój: wesoły.')
        result = ExplanationAgent.recommendation_reason(('Dramat',), ('Dramat',), mood='refleksyjny')
        self.assertEqual(result, 'W profilu lubisz gatunek Dramat; ta pozycja ma go w katalogu. Szukany nastrój: refleksyjny.')
        self.assertNotIn('Szukany nastrój', ExplanationAgent.recommendation_reason(('Dramat',), ('Dramat',)))

    def setUp(self):
        self.client = MagicMock(model='test')
        self.selected = (RankedCandidate(candidate(1), .9, .8, .86, 'selected', 1, 'Pasuje.'),)
        self.payload = {'explanations': [{'content_id': 1,
            'explanation': 'Motyw tajemnicy odpowiada Twojej prośbie o mroczny thriller.',
            'evidence': 'Mroczna tajemnica.'}]}
        self.client.chat.return_value = response(self.payload)
        self.agent = ExplanationAgent(self.client)

    def test_model_selects_evidence_and_server_renders_verified_facts(self):
        result = self.agent.run('Mroczny thriller', profile(), self.selected)
        self.assertEqual(result.source, 'model')
        self.assertIn('Mroczna tajemnica.', result.explanations[0].explanation)
        self.assertIn('8.0/10', result.explanations[0].explanation)
        self.assertNotIn(self.payload['explanations'][0]['explanation'], result.message)
        self.assertIn('1. Film 1 —', result.message)
        self.assertEqual(result.prompt_tokens, 20)
        self.assertEqual(result.generated_tokens, 10)
        payload = self.client.chat.call_args.args[0][1]['content']
        self.assertIn('Mroczna tajemnica.', payload)
        self.assertIn('current_request', payload)

    def test_falls_back_for_unsupported_evidence_or_claim(self):
        for change in ({'evidence':'Nieistniejąca scena.'},
                       {'explanation':'Film gwarantuje happy end.'},
                       {'explanation':'<script>alert(1)</script>'},
                       {'content_id': True}, {'content_id':999}):
            with self.subTest(change=change):
                row = {**self.payload['explanations'][0], **change}
                self.client.chat.return_value = response({'explanations':[row]})
                result = self.agent.run('Thriller', profile(), self.selected)
                self.assertEqual(result.source, 'catalog')
                self.assertEqual(result.fallback_reason,'ExplanationAgentError')

    def test_timeout_keeps_catalog_recommendation(self):
        self.client.chat.side_effect = OllamaUnavailableError('timeout')
        result = self.agent.run('Thriller',profile(),self.selected)
        self.assertEqual(result.source,'catalog')
        self.assertIn('Film 1',result.message)

    def test_catalog_warnings_survive_model_generation(self):
        result = self.agent.run('Thriller bez przemocy',profile(),self.selected)
        self.assertEqual(result.source,'model')
        self.assertIn('nie mogę potwierdzić',result.message)

    def test_schema_limits_count_ids_and_evidence_for_current_selection(self):
        self.agent.run('Thriller', profile(), self.selected)
        schema = self.client.chat.call_args.kwargs['response_format']
        rows = schema['properties']['explanations']
        self.assertEqual(rows['minItems'], 1)
        self.assertEqual(rows['maxItems'], 1)
        self.assertEqual(rows['items']['properties']['content_id']['enum'], [1])
        self.assertIn('Mroczna tajemnica.', rows['items']['properties']['evidence']['enum'])

    def test_retries_invalid_quote_and_preserves_total_usage(self):
        bad = {'explanations': [{**self.payload['explanations'][0], 'evidence': 'Parafraza.'}]}
        self.client.chat.side_effect = [response(bad), response(self.payload)]
        result = self.agent.run('Thriller', profile(), self.selected)
        self.assertEqual(result.source, 'model_retry')
        self.assertEqual(result.prompt_tokens, 40)
        self.assertEqual(result.generated_tokens, 20)
        self.assertEqual(result.validation_errors, ('Evidence absent from catalog.',))
        self.assertIn('Popraw poprzedni błąd', self.client.chat.call_args.args[0][0]['content'])

    def test_repeated_invalid_output_has_bounded_retry_and_diagnostics(self):
        self.client.chat.return_value = response({'explanations': []})
        result = self.agent.run('Thriller', profile(), self.selected)
        self.assertEqual(result.source, 'catalog')
        self.assertEqual(self.client.chat.call_count, 2)
        self.assertEqual(len(result.validation_errors), 2)

    def test_false_absence_of_violence_is_rejected(self):
        self.client.chat.return_value = response({'explanations': [{
            **self.payload['explanations'][0], 'explanation': 'Film nie zawiera przemocy.'}]})
        result = self.agent.run('Bez przemocy', profile(), self.selected)
        self.assertEqual(result.source, 'catalog')

    def test_evidence_must_belong_to_its_candidate(self):
        from dataclasses import replace
        second = RankedCandidate(replace(candidate(2), overview='Inna historia.', genres=('Komedia',)),
                                 .8, .8, .8, 'selected', 2, 'Pasuje.')
        self.client.chat.return_value = response({'explanations': [
            self.payload['explanations'][0],
            {'content_id': 2, 'explanation': 'Dopasowanie.', 'evidence': 'Mroczna tajemnica.'}]})
        result = self.agent.run('Thriller', profile(), (*self.selected, second))
        self.assertEqual(result.source, 'catalog')

    def test_excerpts_preserve_literal_source_and_length(self):
        from dataclasses import replace
        item = replace(candidate(1), overview='Długi opis ' * 100)
        for quote in self.agent._evidence_options(item):
            self.assertLessEqual(len(quote), 300)
            self.assertTrue(quote in item.overview or quote in item.genres)
