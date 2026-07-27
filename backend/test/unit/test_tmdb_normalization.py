from datetime import date

from django.test import SimpleTestCase

from backend.accounts.management.commands.seed_demo_data import (
    bounded_float,
    normalize_tmdb_item,
    parse_date,
)
from backend.api.genre_normalization import canonical_genre_ids, canonical_genres


class TmdbNormalizationTests(SimpleTestCase):
    def test_splits_tmdb_tv_composite_genres_into_shared_categories(self):
        self.assertEqual(
            canonical_genres(
                {
                    10759: "Akcja i Przygoda",
                    10765: "Sci-Fi i Fantasy",
                    10768: "War & Politics",
                }
            ),
            {
                28: "Akcja",
                12: "Przygodowy",
                878: "Science Fiction",
                14: "Fantasy",
                10752: "Wojenny",
                10768: "Polityczny",
            },
        )
        self.assertEqual(
            canonical_genre_ids((10765, 14, 10759, 10768)),
            (878, 14, 28, 12, 10752, 10768),
        )

    def test_normalizes_movie_from_tmdb(self):
        item = normalize_tmdb_item(
            {
                "id": 210577,
                "title": "Zaginiona dziewczyna",
                "original_title": "Gone Girl",
                "overview": "Opis",
                "release_date": "2014-10-01",
                "original_language": "en",
                "poster_path": "/poster.jpg",
                "backdrop_path": "/backdrop.jpg",
                "vote_average": 8.1,
                "vote_count": 19000,
                "popularity": 78.4,
                "genre_ids": [18, 53, "invalid"],
                "adult": False,
            },
            "movie",
        )

        self.assertIsNotNone(item)
        self.assertEqual(item.tmdb_id, 210577)
        self.assertEqual(item.media_type, "movie")
        self.assertEqual(item.release_date, date(2014, 10, 1))
        self.assertEqual(item.genre_ids, (18, 53))
        self.assertEqual(item.metadata["source"], "tmdb")
        self.assertEqual(item.metadata["voteCount"], 19000)

    def test_normalizes_tv_show_and_rejects_invalid_rows(self):
        item = normalize_tmdb_item(
            {
                "id": 70523,
                "name": "Dark",
                "original_name": "Dark",
                "first_air_date": "2017-12-01",
                "origin_country": ["DE"],
                "genre_ids": [18, 9648],
            },
            "tv",
        )

        self.assertIsNotNone(item)
        self.assertEqual(item.title, "Dark")
        self.assertEqual(item.release_date, date(2017, 12, 1))
        self.assertEqual(item.metadata["originCountry"], ["DE"])
        self.assertIsNone(normalize_tmdb_item({"id": 1}, "movie"))
        self.assertIsNone(normalize_tmdb_item({"id": 1, "title": "Film"}, "person"))

    def test_invalid_external_values_are_safely_replaced_with_null(self):
        item = normalize_tmdb_item(
            {
                "id": 1,
                "title": "Niepełne dane",
                "release_date": "not-a-date",
                "vote_average": 14,
                "popularity": -2,
                "vote_count": -1,
                "genre_ids": None,
            },
            "movie",
        )

        self.assertIsNotNone(item)
        self.assertIsNone(item.release_date)
        self.assertIsNone(item.vote_average)
        self.assertIsNone(item.popularity)
        self.assertIsNone(item.metadata["voteCount"])
        self.assertEqual(item.genre_ids, ())
        self.assertIsNone(parse_date("2026-02-31"))
        self.assertIsNone(bounded_float(True, 0, 10))

