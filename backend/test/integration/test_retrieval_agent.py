from django.db import connection
from django.test import override_settings

from backend.recommendation_agents.profiling import (
    ProfilingAgentOutput,
    ProfilingConstraints,
)
from backend.recommendation_agents.retrieval import RetrievalAgent
from backend.test.integration.api_base import ApiIntegrationTestCase


def multi_genre_profile() -> ProfilingAgentOutput:
    return ProfilingAgentOutput(
        intent="recommendation",
        mood=None,
        media_types=("movie",),
        genres=("Horror", "Science Fiction"),
        themes=(),
        avoid=(),
        reference_titles=(),
        constraints=ProfilingConstraints(None, None, None, None),
        needs_clarification=False,
        clarification_question=None,
        confidence=1.0,
        evidence=("Horror science fiction",),
    )


@override_settings(
    LLM_SEMANTIC_SEARCH_ENABLED=False,
    LLM_CATALOG_CANDIDATE_LIMIT=12,
)
class RetrievalGenreIntersectionTests(ApiIntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.genre_ids = {}
        with connection.cursor() as cursor:
            for tmdb_genre_id, name in (
                (27, "Horror"),
                (878, "Science Fiction"),
                (10762, "Dla dzieci"),
                (10751, "Familijny"),
                (35, "Komedia"),
            ):
                cursor.execute(
                    """
                    INSERT INTO genre (tmdb_genre_id, name)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    [tmdb_genre_id, name],
                )
                self.genre_ids[name] = cursor.fetchone()[0]

    def attach_genres(self, content_id: int, *genre_names: str) -> None:
        with connection.cursor() as cursor:
            for name in genre_names:
                cursor.execute(
                    "INSERT INTO content_genre (content_id, genre_id) VALUES (%s, %s)",
                    [content_id, self.genre_ids[name]],
                )

    def test_returns_only_intersection_when_at_least_one_title_has_all_genres(self):
        both_id = self.insert_content(1001, "Horror science fiction")
        horror_id = self.insert_content(1002, "Czysty horror")
        science_fiction_id = self.insert_content(1003, "Czyste science fiction")
        self.attach_genres(both_id, "Horror", "Science Fiction")
        self.attach_genres(horror_id, "Horror")
        self.attach_genres(science_fiction_id, "Science Fiction")

        run = RetrievalAgent(None).run(
            "Horror science fiction",
            multi_genre_profile(),
        )

        self.assertEqual(
            [candidate.content_id for candidate in run.candidates],
            [both_id],
        )

    def test_falls_back_to_or_when_no_title_has_all_genres(self):
        horror_id = self.insert_content(1001, "Czysty horror")
        science_fiction_id = self.insert_content(1002, "Czyste science fiction")
        self.attach_genres(horror_id, "Horror")
        self.attach_genres(science_fiction_id, "Science Fiction")

        run = RetrievalAgent(None).run(
            "Horror science fiction",
            multi_genre_profile(),
        )

        self.assertEqual(
            {candidate.content_id for candidate in run.candidates},
            {horror_id, science_fiction_id},
        )

    def test_child_movie_request_accepts_catalog_family_movies(self):
        family_movie_id = self.insert_content(1004, "Familijny film")
        self.attach_genres(family_movie_id, "Familijny")
        child_profile = ProfilingAgentOutput(
            **{
                **multi_genre_profile().__dict__,
                "genres": ("Dla dzieci",),
            }
        )

        run = RetrievalAgent(None).run(
            "Film dla sześciolatka",
            child_profile,
        )

        self.assertEqual(
            [candidate.content_id for candidate in run.candidates],
            [family_movie_id],
        )

    def test_light_request_does_not_return_plain_drama(self):
        comedy_id = self.insert_content(1005, "Lekka komedia")
        drama_id = self.insert_content(1006, "Ciężki dramat")
        self.attach_genres(comedy_id, "Komedia")
        self.attach_genres(drama_id, "Horror")
        light_profile = ProfilingAgentOutput(
            **{
                **multi_genre_profile().__dict__,
                "genres": (),
                "themes": ("lekki klimat",),
            }
        )

        run = RetrievalAgent(None).run("Lekki film", light_profile)

        self.assertEqual(
            [candidate.content_id for candidate in run.candidates],
            [comedy_id],
        )

    def test_content_question_retrieves_only_referenced_previous_title(self):
        referenced_id = self.insert_content(1007, "Luca")
        self.insert_content(1008, "Inny film")
        question_profile = ProfilingAgentOutput(
            **{
                **multi_genre_profile().__dict__,
                "intent": "content_question",
                "genres": (),
                "reference_titles": ("Luca",),
            }
        )

        run = RetrievalAgent(None).run(
            "Kto reżyserował pierwszą propozycję?",
            question_profile,
        )

        self.assertEqual(
            [candidate.content_id for candidate in run.candidates],
            [referenced_id],
        )

    def test_strong_heroine_theme_excludes_unrelated_male_story(self):
        heroine_id = self.insert_content(1009, "Historia bohaterki")
        unrelated_id = self.insert_content(1010, "Historia złodzieja")
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE content SET overview = %s WHERE id = %s",
                ["Młoda kobieta walczy o swoją rodzinę.", heroine_id],
            )
            cursor.execute(
                "UPDATE content SET overview = %s WHERE id = %s",
                ["Złodziej planuje zemstę za krzywdę ojca.", unrelated_id],
            )
        heroine_profile = ProfilingAgentOutput(
            **{
                **multi_genre_profile().__dict__,
                "genres": (),
                "themes": ("silna bohaterka",),
            }
        )

        run = RetrievalAgent(None).run("Film z silną bohaterką", heroine_profile)

        self.assertEqual(
            [candidate.content_id for candidate in run.candidates],
            [heroine_id],
        )
