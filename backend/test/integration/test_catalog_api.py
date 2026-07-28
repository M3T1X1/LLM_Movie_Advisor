from dataclasses import replace
from datetime import date

from django.core.cache import cache
from django.db import connection
from django.urls import reverse
from django.utils import timezone

from backend.accounts.management.commands.seed_demo_data import (
    Command as SeedDemoCommand,
)
from backend.accounts.management.commands.seed_demo_data import TmdbCatalogItem
from backend.api.models import Content, ContentGenre, Genre, Interaction
from backend.test.integration.api_base import ApiIntegrationTestCase


class CatalogApiTests(ApiIntegrationTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def test_catalog_serializes_database_content_and_genres_to_camel_case(self):
        content_id = self.insert_content()
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO genre (tmdb_genre_id, name) VALUES (53, 'Thriller') RETURNING id"
            )
            genre_id = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO content_genre (content_id, genre_id) VALUES (%s, %s)",
                [content_id, genre_id],
            )

        response = self.client.get(reverse("api:contents"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        content = payload["items"][0]
        self.assertEqual(content["tmdbId"], 1001)
        self.assertEqual(content["mediaType"], "movie")
        self.assertEqual(content["metadata"], {"source": "test"})
        self.assertEqual(content["genres"][0]["name"], "Thriller")
        self.assertEqual(
            payload["pagination"],
            {
                "page": 1,
                "pageSize": 20,
                "totalItems": 1,
                "totalPages": 1,
                "hasPrevious": False,
                "hasNext": False,
            },
        )
        self.assertEqual(payload["filters"]["genres"], ["Thriller"])

    def test_orm_seeder_upserts_catalog_and_relations_idempotently(self):
        item = TmdbCatalogItem(
            tmdb_id=9001,
            media_type="movie",
            title="Film ORM",
            original_title="ORM Movie",
            overview="Opis",
            release_date=date(2026, 1, 2),
            original_language="pl",
            poster_path="/orm.jpg",
            vote_average=8.5,
            popularity=100.0,
            genre_ids=(18, 53),
            metadata={"source": "test"},
        )
        command = SeedDemoCommand()

        catalog = [
            item,
            replace(item, tmdb_id=9002, title="Drugi film ORM"),
            replace(item, tmdb_id=9003, title="Trzeci film ORM"),
        ]
        first_ids = command._seed_catalog(
            {18: "Dramat", 53: "Thriller"},
            catalog,
        )
        second_ids = command._seed_catalog(
            {18: "Dramat", 53: "Thriller"},
            [replace(item, title="Film ORM po aktualizacji"), *catalog[1:]],
        )

        self.assertEqual(first_ids, second_ids)
        content = Content.objects.get(pk=first_ids[0])
        self.assertEqual(content.title, "Film ORM po aktualizacji")
        self.assertEqual(
            set(content.genres.values_list("name", flat=True)),
            {"Dramat", "Thriller"},
        )
        self.assertEqual(Genre.objects.count(), 2)
        conversation_ids, candidates = command._seed_recommendation_history(
            [self.business_user_id],
            first_ids,
        )
        command._seed_interactions(
            [self.business_user_id],
            first_ids,
            candidates,
        )
        self.assertEqual(len(conversation_ids), 5)
        self.assertEqual(len(candidates), 12)
        self.assertEqual(Interaction.objects.count(), 30)

    def test_orm_seeder_normalizes_composite_tv_genres(self):
        item = TmdbCatalogItem(
            tmdb_id=9100,
            media_type="tv",
            title="Serial ze złożonymi gatunkami",
            original_title="Composite Genres",
            overview="Opis",
            release_date=date(2026, 2, 3),
            original_language="en",
            poster_path="/genres.jpg",
            vote_average=7.5,
            popularity=80.0,
            genre_ids=(10759, 10765, 10768),
            metadata={"source": "test"},
        )

        content_id = SeedDemoCommand()._seed_catalog(
            {
                10759: "Akcja i Przygoda",
                10765: "Sci-Fi i Fantasy",
                10768: "War & Politics",
            },
            [item],
        )[0]

        self.assertEqual(
            set(
                Content.objects.get(pk=content_id).genres.values_list(
                    "name",
                    flat=True,
                )
            ),
            {
                "Akcja",
                "Przygodowy",
                "Science Fiction",
                "Fantasy",
                "Wojenny",
                "Polityczny",
            },
        )
        self.assertFalse(
            Genre.objects.filter(tmdb_genre_id__in=(10759, 10765)).exists()
        )

    def test_catalog_paginates_and_filters_the_full_database_query(self):
        content_ids = []
        for index in range(25):
            content_ids.append(
                self.insert_content(
                    tmdb_id=2000 + index,
                    title=f"Tytuł {index:02d}",
                )
            )

        page_response = self.client.get(
            reverse("api:contents"),
            {
                "page": 2,
                "page_size": 10,
                "sort": "title",
            },
        )
        filtered_response = self.client.get(
            reverse("api:contents"),
            {
                "q": "Tytuł 1",
                "media_type": "movie",
                "min_rating": "8",
                "year_from": str(timezone.now().year),
                "sort": "title",
            },
        )
        selected_response = self.client.get(
            reverse("api:contents"),
            {
                "ids": f"{content_ids[2]},{content_ids[20]}",
                "page_size": 50,
            },
        )

        self.assertEqual(page_response.status_code, 200)
        page_payload = page_response.json()
        self.assertEqual(page_payload["pagination"]["totalItems"], 25)
        self.assertEqual(page_payload["pagination"]["totalPages"], 3)
        self.assertTrue(page_payload["pagination"]["hasPrevious"])
        self.assertTrue(page_payload["pagination"]["hasNext"])
        self.assertEqual(len(page_payload["items"]), 10)
        self.assertEqual(page_payload["items"][0]["title"], "Tytuł 10")
        self.assertEqual(page_payload["items"][-1]["title"], "Tytuł 19")

        self.assertEqual(filtered_response.status_code, 200)
        filtered_payload = filtered_response.json()
        self.assertEqual(filtered_payload["pagination"]["totalItems"], 10)
        self.assertEqual(
            [item["title"] for item in filtered_payload["items"]],
            [f"Tytuł {index:02d}" for index in range(10, 20)],
        )
        self.assertEqual(selected_response.status_code, 200)
        self.assertEqual(
            {item["id"] for item in selected_response.json()["items"]},
            {str(content_ids[2]), str(content_ids[20])},
        )

    def test_catalog_reuses_cached_search_and_separates_query_variants(self):
        content_id = self.insert_content(title="Thriller z cache")
        query = {
            "q": "thriller",
            "page": 1,
            "page_size": 20,
            "sort": "popularity",
        }

        first_response = self.client.get(reverse("api:contents"), query)
        Content.objects.filter(pk=content_id).update(title="Tytuł po zmianie")
        cached_response = self.client.get(reverse("api:contents"), query)
        different_sort_response = self.client.get(
            reverse("api:contents"),
            {**query, "sort": "rating"},
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(
            first_response.json()["items"][0]["title"],
            "Thriller z cache",
        )
        self.assertEqual(
            cached_response.json()["items"][0]["title"],
            "Thriller z cache",
        )
        self.assertEqual(
            different_sort_response.json()["items"][0]["title"],
            "Tytuł po zmianie",
        )

    def test_catalog_seed_invalidates_cached_search_results(self):
        item = TmdbCatalogItem(
            tmdb_id=9200,
            media_type="movie",
            title="Tytuł przed synchronizacją",
            original_title="Synchronized Movie",
            overview="Opis",
            release_date=date(2026, 10, 1),
            original_language="pl",
            poster_path="/sync.jpg",
            vote_average=8.0,
            popularity=70.0,
            genre_ids=(18,),
            metadata={"source": "test"},
        )
        command = SeedDemoCommand()
        command._seed_catalog({18: "Dramat"}, [item])
        query = {"q": "synchronized movie"}

        cached_response = self.client.get(reverse("api:contents"), query)
        command._seed_catalog(
            {18: "Dramat"},
            [replace(item, title="Tytuł po synchronizacji")],
        )
        refreshed_response = self.client.get(reverse("api:contents"), query)

        self.assertEqual(
            cached_response.json()["items"][0]["title"],
            "Tytuł przed synchronizacją",
        )
        self.assertEqual(
            refreshed_response.json()["items"][0]["title"],
            "Tytuł po synchronizacji",
        )

    def test_catalog_rejects_invalid_pagination_and_filter_values(self):
        invalid_queries = (
            {"page": "0"},
            {"page": "abc"},
            {"page_size": "51"},
            {"sort": "random"},
            {"media_type": "documentary"},
            {"min_rating": "11"},
            {"year_from": "1800"},
            {"ids": "1,nie-liczba"},
        )

        for query in invalid_queries:
            with self.subTest(query=query):
                response = self.client.get(reverse("api:contents"), query)
                self.assertEqual(response.status_code, 400)
                self.assertIn("detail", response.json())

    def test_catalog_validates_all_remaining_boundaries(self):
        valid_id = self.insert_content()
        invalid_queries = (
            {"q": "x" * 201},
            {"genre": "x" * 101},
            {"min_rating": "not-a-number"},
            {"year_from": "not-a-year"},
            {"ids": ""},
            {"ids": "0"},
            {"ids": "-1"},
            {"ids": ",".join(str(index) for index in range(1, 52))},
        )
        for query in invalid_queries:
            with self.subTest(query=query):
                response = self.client.get(reverse("api:contents"), query)
                if query == {"ids": ""}:
                    self.assertEqual(response.status_code, 200)
                else:
                    self.assertEqual(response.status_code, 400)
                    self.assertIn("detail", response.json())

        boundary_response = self.client.get(
            reverse("api:contents"),
            {
                "q": "x" * 200,
                "genre": "x" * 100,
                "min_rating": "0",
                "year_from": "1888",
            },
        )
        duplicate_ids = self.client.get(
            reverse("api:contents"),
            {"ids": f"{valid_id},{valid_id}", "page_size": 50},
        )
        beyond_last_page = self.client.get(
            reverse("api:contents"),
            {"page": 999},
        )
        self.assertEqual(boundary_response.status_code, 200)
        self.assertEqual(len(duplicate_ids.json()["items"]), 1)
        self.assertEqual(beyond_last_page.status_code, 200)
        self.assertEqual(beyond_last_page.json()["items"], [])
        self.assertFalse(beyond_last_page.json()["pagination"]["hasNext"])

    def test_catalog_searches_original_title_filters_genre_case_insensitively_and_sorts_nulls_last(
        self,
    ):
        null_id = self.insert_content(6001, "Bez oceny")
        matching_id = self.insert_content(6002, "Polski tytuł")
        Content.objects.filter(pk=null_id).update(vote_average=None)
        Content.objects.filter(pk=matching_id).update(
            original_title="Unique Original",
            vote_average=9,
        )
        genre = Genre.objects.create(tmdb_genre_id=6002, name="Thriller")
        ContentGenre.objects.create(content_id=matching_id, genre=genre)

        searched = self.client.get(
            reverse("api:contents"),
            {"q": "unique original"},
        )
        filtered = self.client.get(
            reverse("api:contents"),
            {"genre": "thriller"},
        )
        sorted_response = self.client.get(
            reverse("api:contents"),
            {"sort": "rating"},
        )

        self.assertEqual(
            [item["id"] for item in searched.json()["items"]],
            [str(matching_id)],
        )
        self.assertEqual(
            [item["id"] for item in filtered.json()["items"]],
            [str(matching_id)],
        )
        self.assertEqual(sorted_response.json()["items"][-1]["id"], str(null_id))
