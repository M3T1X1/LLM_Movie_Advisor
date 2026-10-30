
from django.test import override_settings

from backend.api.catalog_sync import upsert_catalog
from backend.api.models import Content, ContentGenre, Genre
from backend.recommendation_agents.retrieval import RetrievalAgent
from backend.test.integration.api_base import ApiIntegrationTestCase
from backend.test.unit.test_recommendation_agents import profile
from backend.tmdb import normalize_tmdb_item


@override_settings(LLM_SEMANTIC_SEARCH_ENABLED=False)
class ManualChatRetrievalRegressions(ApiIntegrationTestCase):
    def test_space_filter_rejects_earthbound_epidemic(self):
        space = self.insert_content(1001, 'Kosmiczna wyprawa')
        earth = self.insert_content(1002, 'Epidemia')
        genre = Genre.objects.create(tmdb_genre_id=878, name='Science Fiction')
        for pk in (space, earth):
            ContentGenre.objects.create(content_id=pk, genre=genre)
        Content.objects.filter(pk=space).update(overview='Astronauci lecą przez kosmos.')
        Content.objects.filter(pk=earth).update(overview='Przybysz z nieznanej planety wywołuje epidemię na Ziemi.')
        result = RetrievalAgent(None).run('Poleć science fiction o kosmosie',
            profile(genres=('Science Fiction',), themes=('podróż kosmiczna',)))
        self.assertEqual([c.content_id for c in result.candidates], [space])

    def test_country_filter_requires_verified_country(self):
        korean = self.insert_content(1001, 'Koreański thriller')
        chinese = self.insert_content(1002, 'Inny thriller')
        Content.objects.filter(pk=korean).update(metadata={'originCountry': ['KR']})
        Content.objects.filter(pk=chinese).update(metadata={'originCountry': ['CN']})
        result = RetrievalAgent(None).run('Poleć koreański thriller',
            profile(genres=(), themes=(), origin_countries=('KR',)))
        self.assertEqual([c.content_id for c in result.candidates], [korean])

    def test_catalog_refresh_preserves_enriched_country(self):
        pk = self.insert_content(1001, 'Film')
        Content.objects.filter(pk=pk).update(metadata={'originCountry': ['PL']})
        item = normalize_tmdb_item({'id': 1001, 'title': 'Film', 'genre_ids': []}, 'movie')
        upsert_catalog({}, [item])
        self.assertEqual(Content.objects.get(pk=pk).metadata['originCountry'], ['PL'])

    def test_negated_animation_is_excluded_from_retrieval(self):
        comedy = Genre.objects.create(tmdb_genre_id=35, name='Komedia')
        animation = Genre.objects.create(tmdb_genre_id=16, name='Animacja')
        live = self.insert_content(1001, 'Komedia aktorska')
        animated = self.insert_content(1002, 'Animowana komedia')
        for pk in (live, animated):
            ContentGenre.objects.create(content_id=pk, genre=comedy)
        ContentGenre.objects.create(content_id=animated, genre=animation)
        from backend.recommendation_agents.profiling import ProfilingAgent, ProfilingAgentInput
        text = 'Komedia, ale nie animacja.'
        output = ProfilingAgent._ground_output(ProfilingAgentInput(text), ProfilingAgent._fallback_output(text))
        result = RetrievalAgent(None).run(text, output)
        self.assertEqual([c.content_id for c in result.candidates], [live])

    def test_negated_space_is_a_hard_filter(self):
        earth = self.insert_content(1001, 'Ziemska historia')
        space = self.insert_content(1002, 'Wyprawa')
        Content.objects.filter(pk=earth).update(overview='Naukowiec buduje robota w mieście.')
        Content.objects.filter(pk=space).update(overview='Astronauci wyruszają w kosmos.')
        comet = self.insert_content(1003, 'Kometa')
        Content.objects.filter(pk=comet).update(overview='Astronomowie ostrzegają przed kometą.')
        result = RetrievalAgent(None).run('Nie o kosmosie',
            profile(genres=(), themes=(), excluded_themes=('podróż kosmiczna',)))
        self.assertEqual([c.content_id for c in result.candidates], [earth])
