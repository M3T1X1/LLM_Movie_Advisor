"""Hard constraints remain effective even with maximal model scores."""
from dataclasses import replace
from unittest.mock import MagicMock
from django.test import SimpleTestCase
from backend.recommendation_agents.profiling import ProfilingConstraints
from backend.recommendation_agents.ranking import RankingAgent, RankedCandidate
from backend.recommendation_agents.explanation import ExplanationAgent
from backend.recommendation_agents.request_rules import candidate_violations
from backend.test.unit.test_recommendation_agents import candidate, profile, response
from backend.test.unit.llm_cases import cases, expand_cases

LIMIT = ProfilingConstraints
CONSTRAINTS = [
    ('media', {'media_types': ('tv',)}, {}, 'media_type'),
    ('excluded_id', {'excluded_content_ids': (1,)}, {}, 'excluded_title'),
    ('genre', {'genres': ('Komedia',)}, {}, 'genres'),
    ('all_genres', {'genres': ('Thriller', 'Komedia'), 'genre_match_mode': 'all'}, {}, 'genres'),
    ('excluded_genre', {'avoid': ('Thriller',)}, {}, 'excluded_genre'),
    ('country_unknown', {'origin_countries': ('PL',)}, {}, 'origin_country'),
    ('country_wrong', {'origin_countries': ('PL',)}, {'origin_countries': ('US',)}, 'origin_country'),
    ('excluded_country', {'excluded_origin_countries': ('US',)}, {'origin_countries': ('US',)}, 'excluded_country'),
    ('excluded_country_unknown', {'excluded_origin_countries': ('US',)}, {}, 'excluded_country'),
    ('language', {'original_languages': ('pl',)}, {'original_language': 'en'}, 'original_language'),
    ('year_from', {'constraints': LIMIT(None, 2021, None, None)}, {}, 'release_year_from'),
    ('year_to', {'constraints': LIMIT(None, None, 2019, None)}, {}, 'release_year_to'),
    ('year_unknown', {'constraints': LIMIT(None, 2010, None, None)}, {'release_date': None}, 'release_year_from'),
    ('rating', {'constraints': LIMIT(None, None, None, 9)}, {}, 'min_vote_average'),
    ('rating_unknown', {'constraints': LIMIT(None, None, None, 7)}, {'vote_average': None}, 'min_vote_average'),
    ('runtime', {'constraints': LIMIT(90, None, None, None)}, {}, 'max_runtime_minutes'),
    ('runtime_unknown', {'constraints': LIMIT(90, None, None, None)}, {'metadata': {}}, 'max_runtime_minutes'),
    ('runtime_bool', {'constraints': LIMIT(90, None, None, None)}, {'metadata': {'runtimeMinutes': True}}, 'max_runtime_minutes'),
    ('runtime_zero', {'constraints': LIMIT(90, None, None, None)}, {'metadata': {'runtimeMinutes': 0}}, 'max_runtime_minutes'),
    ('runtime_negative', {'constraints': LIMIT(90, None, None, None)}, {'metadata': {'runtimeMinutes': -1}}, 'max_runtime_minutes'),
    ('clarification', {'needs_clarification': True}, {}, 'clarification_required'),
]


@expand_cases
class HardConstraintMatrixTests(SimpleTestCase):
    @cases(CONSTRAINTS)
    def test_gate_identifies_violation(self, constraints, changes, reason):
        self.assertIn(reason, candidate_violations(replace(candidate(1), **changes), profile(themes=(), **constraints)))

    @cases(CONSTRAINTS)
    def test_perfect_model_score_cannot_override_constraint(self, constraints, changes, reason):
        client = MagicMock(model='test')
        client.chat.return_value = response({'scores': [{'content_id': 1, 'relevance_score': 1, 'critic_score': 1, 'decision_reason': 'Idealnie pasuje.'}]})
        result = RankingAgent(client).run('Poleć film', profile(themes=(), **constraints), (replace(candidate(1), **changes),))
        self.assertEqual(result.selected, ())

    @cases(CONSTRAINTS)
    def test_explanation_does_not_reintroduce_invalid_title(self, constraints, changes, reason):
        client = MagicMock(model='test')
        selected = (RankedCandidate(replace(candidate(1), **changes), 1, 1, 1, 'selected', 1, 'Opis.'),)
        result = ExplanationAgent(client).run('Poleć film', profile(themes=(), **constraints), selected)
        self.assertEqual(result.explanations, ())
        client.chat.assert_not_called()

    @cases([('runtime', LIMIT(110, None, None, None)), ('year_from', LIMIT(None, 2020, None, None)),
            ('year_to', LIMIT(None, None, 2020, None)), ('rating', LIMIT(None, None, None, 8))])
    def test_inclusive_boundary_is_accepted(self, limits):
        self.assertEqual(candidate_violations(candidate(1), profile(themes=(), constraints=limits)), ())
