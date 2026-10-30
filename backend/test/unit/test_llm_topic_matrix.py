"""Catalog evidence must survive selection, exclusions and model failure."""
from dataclasses import replace
from unittest.mock import MagicMock
from django.test import SimpleTestCase
from backend.ollama import OllamaUnavailableError
from backend.recommendation_agents.explanation import ExplanationAgent
from backend.recommendation_agents.ranking import RankingAgent, RankedCandidate
from backend.recommendation_agents.request_rules import candidate_violations
from backend.test.unit.test_recommendation_agents import candidate, profile, response
from backend.test.unit.llm_cases import cases, expand_cases

# Hand-written examples, independent of production regex vocabulary.
TOPICS = [
    ('space', 'podróż kosmiczna', 'Astronauta dociera na orbitę.', 'Bohater przegląda spacery po mieście.'),
    ('time', 'podróże w czasie', 'Bohater buduje wehikuł czasu.', 'Zegarmistrz naprawia zegarek.'),
    ('ai', 'sztuczna inteligencja', 'Sztuczna inteligencja przejmuje statek.', 'Nauczyciel ceni inteligencję uczniów.'),
    ('survival', 'przetrwanie', 'Rozbitkowie walczą o przetrwanie.', 'Podróżnicy planują wakacje.'),
    ('friendship', 'przyjaźń', 'Przyjaźń łączy dwie sąsiadki.', 'Obcy ludzie czekają na autobus.'),
    ('heist', 'napad na bank', 'Złodzieje planują napad na bank.', 'Bankier planuje urlop.'),
    ('investigation', 'śledztwo', 'Detektyw prowadzi śledztwo.', 'Listonosz roznosi listy.'),
    ('war', 'wojna', 'Żołnierze wracają z wojny.', 'Edward otwiera warsztat.'),
    ('loneliness', 'samotność', 'Astronauta jest samotny.', 'Lądują na oddalonej planecie.'),
    ('music', 'muzyka', 'Piosenkarka przygotowuje koncert.', 'Księgowa przygotowuje raport.'),
    ('hackers', 'hakerzy', 'Hakerzy przejmują sieć.', 'Mechanik naprawia samochód.'),
]


@expand_cases
class TopicEvidenceMatrixTests(SimpleTestCase):
    @cases(TOPICS)
    def test_catalog_accepts_confirmed_theme(self, theme, evidence, decoy):
        p = profile(genres=(), themes=(theme,))
        self.assertEqual(candidate_violations(replace(candidate(1), overview=evidence), p), ())

    @cases(TOPICS)
    def test_catalog_rejects_decoy(self, theme, evidence, decoy):
        p = profile(genres=(), themes=(theme,))
        self.assertIn('topic:' + theme, candidate_violations(replace(candidate(1), overview=decoy), p))

    @cases(TOPICS)
    def test_excluded_theme_rejects_confirmed_candidate(self, theme, evidence, decoy):
        p = profile(genres=(), themes=(), excluded_themes=(theme,))
        self.assertIn('excluded_topic:' + theme, candidate_violations(replace(candidate(1), overview=evidence), p))
        self.assertEqual(candidate_violations(replace(candidate(1), overview=decoy), p), ())

    @cases(TOPICS)
    def test_model_score_cannot_override_missing_theme(self, theme, evidence, decoy):
        client = MagicMock(model='test')
        client.chat.return_value = response({'scores': [
            {'content_id': pk, 'relevance_score': score, 'critic_score': score, 'decision_reason': 'Opis.'}
            for pk, score in [(1, 1), (2, .8)]]})
        result = RankingAgent(client).run('Poleć film', profile(genres=(), themes=(theme,), result_count=1), (
            replace(candidate(1), overview=decoy), replace(candidate(2), overview=evidence)))
        self.assertEqual([x.candidate.content_id for x in result.selected], [2])

    @cases(TOPICS)
    def test_explanation_gate_rechecks_bad_selection(self, theme, evidence, decoy):
        client = MagicMock(model='test')
        selected = (RankedCandidate(replace(candidate(1), overview=decoy), 1, 1, 1, 'selected', 1, 'Opis.'),)
        result = ExplanationAgent(client).run('Poleć film', profile(genres=(), themes=(theme,)), selected)
        self.assertEqual(result.explanations, ())
        client.chat.assert_not_called()

    @cases(TOPICS)
    def test_offline_explanation_uses_relevant_later_sentence(self, theme, evidence, decoy):
        client = MagicMock(model='test')
        client.chat.side_effect = OllamaUnavailableError('offline')
        item = replace(candidate(1), overview=f'{decoy} {evidence}')
        selected = (RankedCandidate(item, 1, 1, 1, 'selected', 1, 'Opis.'),)
        result = ExplanationAgent(client).run('Poleć film', profile(genres=(), themes=(theme,), mood=None), selected)
        self.assertIn(evidence, result.explanations[0].explanation)
        self.assertNotIn(decoy, result.explanations[0].explanation)
        self.assertEqual(client.chat.call_count, 1)

    @cases([(label, theme, evidence.upper(), decoy) for label, theme, evidence, decoy in TOPICS])
    def test_uppercase_catalog_evidence(self, theme, evidence, decoy):
        self.assertEqual(candidate_violations(replace(candidate(1), overview=evidence), profile(genres=(), themes=(theme,))), ())
