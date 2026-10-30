
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
