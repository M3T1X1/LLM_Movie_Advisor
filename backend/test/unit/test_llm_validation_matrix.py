"""Malformed model output, bounded retries and evidence isolation."""
from dataclasses import replace
from unittest.mock import MagicMock
from django.test import SimpleTestCase
from backend.recommendation_agents.explanation import ExplanationAgent, ExplanationAgentError
from backend.recommendation_agents.ranking import RankingAgent, RankedCandidate
from backend.test.unit.test_recommendation_agents import candidate, profile, response
from backend.test.unit.llm_cases import cases, expand_cases

BAD_SCORES = [('bool', True), ('null', None), ('negative', -.01), ('too_large', 10.1),
              ('nan', float('nan')), ('infinity', float('inf')), ('text', 'high'), ('list', []), ('object', {})]
BAD_ROWS = [
    ('unknown_id', {'content_id': 99}), ('boolean_id', {'content_id': True}),
    ('string_id', {'content_id': '1'}), ('missing_evidence', {'evidence': None}),
    ('empty_evidence', {'evidence': ''}), ('invented_evidence', {'evidence': 'Obcy atakują Ziemię.'}),
    ('empty_summary', {'summary': ''}), ('blank_summary', {'summary': '   '}),
    ('numeric_summary', {'summary': 3}), ('long_summary', {'summary': 'a'*351}),
    ('html_summary', {'summary': '<b>Opis</b>'}), ('newline_summary', {'summary': 'Opis\nfilmu'}),
    ('guarantee', {'summary': 'Film gwarantuje dobrą zabawę.'}),
    ('unverified_safety', {'summary': 'Film jest bezpieczny dla dzieci.'}),
    ('unverified_dubbing', {'summary': 'Film ma polski dubbing.'}),
    ('rating', {'summary': 'Ocena filmu to 8/10.'}),
    ('extra_field', {'unexpected': 'data'}),
]


@expand_cases
class ModelOutputValidationMatrixTests(SimpleTestCase):
    def setUp(self):
        self.item = RankedCandidate(candidate(1), .9, .9, .9, 'selected', 1, 'Opis.')
        self.client = MagicMock(model='test')
        self.agent = ExplanationAgent(self.client)

    @cases([(f'{field}_{label}', field, value) for field in ('relevance_score', 'critic_score') for label, value in BAD_SCORES])
    def test_invalid_score_is_discarded(self, field, value):
        row = {'content_id': 1, 'relevance_score': .8, 'critic_score': .8, 'decision_reason': 'Opis.'}
        row[field] = value
        self.assertEqual(RankingAgent._validate_scores({'scores': [row]}, (candidate(1),)), {})

    @cases([('zero', 0, 0), ('one', 1, 1), ('decimal', .8, .8), ('ten_scale', 8, .8),
            ('string_decimal', '0.8', .8), ('string_ten', '8', .8)])
    def test_supported_score_formats_normalize(self, value, expected):
        row = {'content_id': 1, 'relevance_score': value, 'critic_score': value, 'decision_reason': ' Opis. '}
        self.assertEqual(RankingAgent._validate_scores({'scores': [row]}, (candidate(1),)), {1: (expected, expected, 'Opis.')})

    @cases(BAD_ROWS)
    def test_bad_explanation_is_rejected(self, changes):
        row = {'content_id': 1, 'evidence': 'Mroczna tajemnica.', 'summary': 'Mroczna tajemnica.', **changes}
        with self.assertRaises(ExplanationAgentError):
            self.agent._validate_explanations({'explanations': [row]}, (self.item,))

    @cases(BAD_ROWS)
    def test_bad_model_output_has_bounded_retry_and_grounded_fallback(self, changes):
        row = {'content_id': 1, 'evidence': 'Mroczna tajemnica.', 'summary': 'Mroczna tajemnica.', **changes}
        self.client.chat.return_value = response({'explanations': [row]})
        result = self.agent.run('Thriller', profile(mood=None), (self.item,))
        self.assertEqual(self.client.chat.call_count, 2)
        self.assertEqual(result.source, 'catalog')
        self.assertEqual(result.explanations[0].explanation, 'Mroczna tajemnica.')
        self.assertEqual(len(result.validation_errors), 2)

    @cases([('null', None), ('array', []), ('string', 'JSON'), ('missing_key', {}),
            ('empty_items', {'explanations': []}), ('wrong_items', {'explanations': {}})])
    def test_invalid_envelope_is_rejected(self, payload):
        with self.assertRaises(ExplanationAgentError):
            self.agent._validate_explanations(payload, (self.item,))

    @cases([('two', 2), ('three', 3)])
    def test_evidence_cannot_be_borrowed_from_another_title(self, count):
        selected = tuple(replace(self.item, candidate=replace(candidate(i), overview=f'Bohater numer {i} podróżuje.')) for i in range(1, count+1))
        rows = [{'content_id': i, 'evidence': f'Bohater numer {i % count + 1} podróżuje.'} for i in range(1, count+1)]
        with self.assertRaises(ExplanationAgentError):
            self.agent._validate_explanations({'explanations': rows}, selected)

    @cases([('two', 2), ('three', 3)])
    def test_duplicate_ids_cannot_replace_missing_explanations(self, count):
        selected = tuple(replace(self.item, candidate=candidate(i)) for i in range(1, count+1))
        rows = [{'content_id': 1, 'evidence': 'Mroczna tajemnica.'} for _ in range(count)]
        with self.assertRaises(ExplanationAgentError):
            self.agent._validate_explanations({'explanations': rows}, selected)
