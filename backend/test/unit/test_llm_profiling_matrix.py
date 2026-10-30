"""Explicit user requirements must survive noisy model interpretations."""
from dataclasses import replace
from unittest.mock import MagicMock
from django.test import SimpleTestCase
from backend.recommendation_agents.profiling import ProfilingAgent, ProfilingAgentInput
from backend.test.unit.test_recommendation_agents import response
from backend.test.unit.test_request_contract import ground
from backend.test.unit.test_profiling_agent import valid_output
from backend.test.unit.llm_cases import cases, expand_cases


@expand_cases
class ProfilingMatrixTests(SimpleTestCase):
    @cases([(f'{count}_{genre}', f'Poleć {quantity} {genre}.', count)
            for count, quantity in [(1, 'jeden film'), (2, 'dwa filmy'), (3, 'trzy filmy')]
            for genre in ['komediowe', 'dramatyczne', 'wojenne', 'science fiction']])
    def test_explicit_count_overrides_model_default(self, prompt, count):
        client = MagicMock()
        # The model schema omits count; grounding must recover it from the request.
        model_profile = valid_output(themes=[], reference_titles=[], avoid=[])
        client.chat.return_value = response(model_profile)
        result = ProfilingAgent(client).run(ProfilingAgentInput(prompt))
        self.assertEqual(result.source, 'model')
        self.assertEqual(result.output.result_count, count)
        self.assertFalse(result.output.needs_clarification)

    @cases([('polish', 'polskim', 'pl'), ('english', 'angielskim', 'en'), ('french', 'francuskim', 'fr'),
            ('japanese', 'japońskim', 'ja'), ('korean', 'koreańskim', 'ko'), ('german', 'niemieckim', 'de'),
            ('spanish', 'hiszpańskim', 'es'), ('italian', 'włoskim', 'it')])
    def test_original_language_does_not_imply_production_country(self, language, code):
        result = ground(f'Poleć film w oryginalnym języku {language}.')
        self.assertEqual(result.original_languages, (code,))
        self.assertEqual(result.origin_countries, ())

    @cases([('nineties', '1990–1999', 1990, 1999), ('millennium', '2000-2009', 2000, 2009),
            ('recent', '2020–2025', 2020, 2025), ('single_year', '2001–2001', 2001, 2001)])
    def test_year_interval_is_preserved(self, text, start, end):
        result = ground(f'Poleć filmy z lat {text}.')
        self.assertEqual(result.constraints.release_year_from, start)
        self.assertEqual(result.constraints.release_year_to, end)

    @cases([('short', 60), ('normal', 90), ('long', 120), ('very_long', 180)])
    def test_runtime_is_not_result_count(self, minutes):
        result = ground(f'Poleć dwa filmy do {minutes} minut.')
        self.assertEqual(result.constraints.max_runtime_minutes, minutes)
        self.assertEqual(result.result_count, 2)

    @cases([('one', (1,)), ('multiple', (1, 2, 3)), ('old_id', (99999,))])
    def test_watched_ids_survive_fresh_request(self, watched):
        result = ground('Poleć jeden thriller.', watched_content_ids=watched)
        self.assertEqual(set(result.excluded_content_ids), set(watched))

    @cases([('one', (1,)), ('multiple', (1, 2, 3)), ('old_id', (99999,))])
    def test_watched_ids_do_not_block_factual_questions(self, watched):
        result = ground('O czym jest ten film?', watched_content_ids=watched)
        self.assertEqual(result.intent, 'content_question')
        self.assertEqual(result.excluded_content_ids, ())

    @cases([('invalid_json', 'not json'), ('truncated', '{"intent":'), ('array', '[]'), ('null', 'null'), ('empty_object', '{}')])
    def test_bad_model_output_preserves_explicit_request_in_fallback(self, content):
        client = MagicMock()
        client.chat.return_value = replace(response({}), content=content)
        result = ProfilingAgent(client).run(ProfilingAgentInput('Poleć dwa thrillery do 100 minut.'))
        self.assertEqual(result.source, 'fallback')
        self.assertEqual(result.output.result_count, 2)
        self.assertEqual(result.output.genres, ('Thriller',))
        self.assertEqual(result.output.constraints.max_runtime_minutes, 100)
        self.assertEqual(client.chat.call_count, 1)

    @cases([('too_many', 'Poleć pięć komedii.'), ('zero', 'Poleć zero filmów.'),
            ('rating', 'Poleć film z oceną minimum 11 na 10.'),
            ('genre_conflict', 'Poleć horror i nie może to być horror.'),
            ('count_conflict', 'Poleć jeden film i jednocześnie trzy filmy.')])
    def test_conflicting_request_requires_clarification(self, prompt):
        self.assertTrue(ground(prompt).needs_clarification)
