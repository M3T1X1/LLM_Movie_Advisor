from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from backend.api.models import (
    ContentGenre,
    Genre,
    RecommendationRun,
    RunCandidate,
)
from backend.test.integration.api_base import ApiIntegrationTestCase


class TrendsApiTests(ApiIntegrationTestCase):
    def test_recommendation_trends_reject_invalid_period_and_support_empty_result(
        self,
    ):
        invalid_response = self.client.get(
            reverse("api:trends"),
            {"period": "year"},
        )
        empty_response = self.client.get(
            reverse("api:trends"),
            {"period": "day"},
        )

        self.assertEqual(invalid_response.status_code, 400)
        self.assertIn("detail", invalid_response.json())
        self.assertEqual(empty_response.status_code, 200)
        self.assertEqual(empty_response.json()["totalRecommendations"], 0)
        self.assertEqual(empty_response.json()["genreTrends"], [])
        self.assertEqual(empty_response.json()["contentTrends"], [])

    def test_recommendation_trends_exclude_candidates_outside_selected_period(
        self,
    ):
        recent_content_id = self.insert_content(3001, "Najnowszy kandydat")
        old_content_id = self.insert_content(3002, "Stary kandydat")
        self.create_recommendation_candidate(
            content_id=recent_content_id,
            created_at=timezone.now() - timedelta(hours=12),
        )
        self.create_recommendation_candidate(
            content_id=old_content_id,
            created_at=timezone.now() - timedelta(days=2),
        )

        day_response = self.client.get(
            reverse("api:trends"),
            {"period": "day"},
        )
        week_response = self.client.get(
            reverse("api:trends"),
            {"period": "week"},
        )

        self.assertEqual(day_response.json()["totalRecommendations"], 1)
        self.assertEqual(
            day_response.json()["contentTrends"][0]["content"]["title"],
            "Najnowszy kandydat",
        )
        self.assertEqual(week_response.json()["totalRecommendations"], 2)

    def test_recommendation_trends_limit_and_order_genres_and_contents(self):
        genres = [
            Genre.objects.create(tmdb_genre_id=4000 + index, name=f"Gatunek {index}")
            for index in range(6)
        ]
        for content_index in range(4):
            content_id = self.insert_content(
                5000 + content_index,
                f"Trend {content_index}",
            )
            for genre in genres[: 6 - content_index]:
                ContentGenre.objects.create(
                    content_id=content_id,
                    genre=genre,
                )
            for _ in range(4 - content_index):
                self.create_recommendation_candidate(content_id=content_id)

        response = self.client.get(
            reverse("api:trends"),
            {"period": "month"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["totalRecommendations"], 10)
        self.assertEqual(len(payload["genreTrends"]), 5)
        self.assertEqual(len(payload["contentTrends"]), 3)
        self.assertEqual(
            [item["recommendationCount"] for item in payload["genreTrends"]],
            sorted(
                [
                    item["recommendationCount"]
                    for item in payload["genreTrends"]
                ],
                reverse=True,
            ),
        )
        self.assertEqual(
            [item["recommendationCount"] for item in payload["contentTrends"]],
            [4, 3, 2],
        )

    def test_recommendation_trends_month_boundary_and_equal_count_tiebreaker(self):
        first_id = self.insert_content(6101, "Pierwszy remis")
        second_id = self.insert_content(6102, "Drugi remis")
        inside = self.create_recommendation_candidate(
            content_id=first_id,
            created_at=timezone.now() - timedelta(days=29, hours=23),
        )
        outside = self.create_recommendation_candidate(
            content_id=second_id,
            created_at=timezone.now() - timedelta(days=31),
        )
        self.assertIsNotNone(inside.pk)
        self.assertIsNotNone(outside.pk)

        response = self.client.get(
            reverse("api:trends"),
            {"period": "month"},
        )

        self.assertEqual(response.json()["totalRecommendations"], 1)
        self.assertEqual(
            response.json()["contentTrends"][0]["content"]["id"],
            str(first_id),
        )

    def test_recommendation_trends_count_only_selected_candidates(self):
        content_id = self.insert_content(6201, "Statusy")
        for status, run_status in (
            ("selected", "completed"),
            ("rejected", "completed"),
            ("pending", "running"),
        ):
            candidate = self.create_recommendation_candidate(content_id=content_id)
            RunCandidate.objects.filter(pk=candidate.pk).update(status=status)
            RecommendationRun.objects.filter(pk=candidate.run_id).update(
                status=run_status
            )

        response = self.client.get(reverse("api:trends"), {"period": "day"})

        self.assertEqual(response.json()["totalRecommendations"], 1)
        self.assertEqual(
            response.json()["contentTrends"][0]["recommendationCount"],
            1,
        )
