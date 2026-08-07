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
            for tmdb_genre_id, name in ((27, "Horror"), (878, "Science Fiction")):
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

