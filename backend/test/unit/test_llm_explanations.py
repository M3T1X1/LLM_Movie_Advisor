import json
from dataclasses import replace
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

    def test_chat_contains_description_without_metadata_or_matching_reason(self):
        result = self.agent.run('Mroczny thriller', profile(), self.selected)
        self.assertEqual(result.source, 'model')
        self.assertIn('Mroczna tajemnica.', result.explanations[0].explanation)
        for unwanted in ('Opis katalogowy', 'Pasuje:', '8.0/10', 'W profilu', 'Szukany nastrój'):
            self.assertNotIn(unwanted, result.message)
        self.assertNotIn(self.payload['explanations'][0]['explanation'], result.message)
        self.assertIn('1. Film 1 —', result.message)
        self.assertEqual(result.prompt_tokens, 20)
        self.assertEqual(result.generated_tokens, 10)
        payload = self.client.chat.call_args.args[0][1]['content']
        self.assertIn('Mroczna tajemnica.', payload)
        self.assertIn('current_request', payload)

    def test_model_paraphrase_is_verified_before_display_and_usage_is_counted(self):
        summary = 'Historia pełna mrocznych zagadek.'
        self.client.chat.side_effect = [
            response({'explanations': [{'content_id': 1, 'evidence': 'Mroczna tajemnica.', 'summary': summary}]}),
            response({'supported': True}),
        ]
        result = self.agent.run('Thriller', profile(), self.selected)
        self.assertEqual(result.source, 'model')
        self.assertIn('1. Film 1 — ' + summary, result.message)
        self.assertEqual(result.prompt_tokens, 40)
        verification = self.client.chat.call_args.args[0][1]['content']
        self.assertIn('Mroczna tajemnica.', verification)
        self.assertIn(summary, verification)

    def test_valid_evidence_does_not_license_invented_summary(self):
        generated = response({'explanations': [{'content_id': 1,
            'evidence': 'Mroczna tajemnica.', 'summary': 'Detektyw szuka zaginionej córki.'}]})
        self.client.chat.side_effect = [generated, response({'supported': False})] * 2
        result = self.agent.run('Thriller', profile(), self.selected)
        self.assertEqual(result.source, 'catalog')
        self.assertNotIn('Detektyw', result.message)
        self.assertIn('Mroczna tajemnica.', result.message)

    def test_each_summary_is_verified_against_only_its_own_catalog_entry(self):
        second = replace(self.selected[0], candidate=replace(
            candidate(2), overview='Młoda pianistka przygotowuje się do koncertu.'), final_rank=2)
        self.client.chat.side_effect = [
            response({'explanations': [
                {'content_id': 1, 'evidence': 'Mroczna tajemnica.', 'summary': 'Historia pełna zagadek.'},
                {'content_id': 2, 'evidence': second.candidate.overview, 'summary': 'Pianistka ćwiczy przed występem.'},
            ]}),
            response({'supported': True}), response({'supported': True}),
        ]
        result = self.agent.run('Thriller', profile(result_count=2), (*self.selected, second))
        self.assertEqual(result.source, 'model')
        checks = [json.loads(call.args[0][1]['content']) for call in self.client.chat.call_args_list[1:]]
        self.assertEqual([check['overview'] for check in checks],
                         ['Mroczna tajemnica.', second.candidate.overview])
        self.assertEqual(result.prompt_tokens, 60)

    def test_invalid_summary_does_not_discard_other_verified_descriptions(self):
        second = replace(self.selected[0], candidate=candidate(2), final_rank=2)
        generated = response({'explanations': [
            {'content_id': 1, 'evidence': 'Mroczna tajemnica.', 'summary': 'Historia pełna zagadek.'},
            {'content_id': 2, 'evidence': 'Mroczna tajemnica.', 'summary': 'Detektyw szuka córki.'},
        ]})
        self.client.chat.side_effect = [generated, response({'supported': True}),
                                      response({'supported': False})] * 2
        result = self.agent.run('Thriller', profile(result_count=2), (*self.selected, second))
        self.assertEqual(result.source, 'model_catalog')
        self.assertIn('1. Film 1 — Historia pełna zagadek.', result.message)
        self.assertIn('2. Film 2 — Mroczna tajemnica.', result.message)
        self.assertNotIn('Detektyw', result.message)

    def test_summary_with_metadata_or_guarantees_is_rejected(self):
        for summary in ('Pasuje: thriller • 2009 • 8.2/10.', 'Film gwarantuje happy end.'):
            with self.subTest(summary=summary):
                self.client.chat.return_value = response({'explanations': [{'content_id': 1,
                    'evidence': 'Mroczna tajemnica.', 'summary': summary}]})
                result = self.agent.run('Thriller', profile(), self.selected)
                self.assertEqual(result.source, 'catalog')
                self.assertNotIn(summary, result.message)

    def test_verifier_transport_failure_uses_plain_catalog_fallback(self):
        self.client.chat.side_effect = [
            response({'explanations': [{'content_id': 1, 'evidence': 'Mroczna tajemnica.',
                                       'summary': 'Historia pełna zagadek.'}]}),
            OllamaUnavailableError('timeout'),
        ]
        result = self.agent.run('Thriller', profile(), self.selected)
        self.assertEqual(result.source, 'catalog')
        self.assertTrue(result.message.endswith('\n1. Film 1 — Mroczna tajemnica.'))
        self.assertNotIn('Historia pełna zagadek.', result.message)

    def test_fallback_without_overview_does_not_invent_plot(self):
        from dataclasses import replace
        item = replace(self.selected[0], candidate=replace(candidate(1), overview=''))
        self.client.chat.side_effect = OllamaUnavailableError('timeout')
        result = self.agent.run('Thriller', profile(), (item,))
        self.assertIn('Gatunek: Thriller.', result.message)
        self.assertNotIn('/10', result.message)

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
