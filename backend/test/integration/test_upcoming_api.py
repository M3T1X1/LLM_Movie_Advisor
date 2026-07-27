from datetime import date, timedelta
from unittest.mock import patch

from django.core.management.base import CommandError
from django.urls import reverse
from django.utils import timezone

from backend.api.models import Content
from backend.test.integration.api_base import ApiIntegrationTestCase


class UpcomingApiTests(ApiIntegrationTestCase):
    @patch("backend.api.views.sync_upcoming_from_tmdb")
    def test_upcoming_uses_fresh_cache_without_contacting_tmdb(self, mocked_sync):
        content_id = self.insert_content(title="Świeża premiera")
        Content.objects.filter(pk=content_id).update(
            release_date=date.today() + timedelta(days=7),
            tmdb_refreshed_at=timezone.now(),
        )

        response = self.client.get(reverse("api:upcoming-contents"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["title"] for item in response.json()],
            ["Świeża premiera"],
        )
        mocked_sync.assert_not_called()

    @patch("backend.api.views.sync_upcoming_from_tmdb")
    def test_upcoming_syncs_stale_cache_and_refresh_forces_sync(self, mocked_sync):
        content_id = self.insert_content(title="Nieaktualna premiera")
        Content.objects.filter(pk=content_id).update(
            release_date=date.today() + timedelta(days=7),
            tmdb_refreshed_at=timezone.now() - timedelta(days=2),
        )

        stale_response = self.client.get(reverse("api:upcoming-contents"))
        refresh_response = self.client.get(
            reverse("api:upcoming-contents"),
            {"refresh": "1"},
        )

        self.assertEqual(stale_response.status_code, 200)
        self.assertEqual(refresh_response.status_code, 200)
        self.assertEqual(mocked_sync.call_count, 2)

    @patch(
        "backend.api.views.sync_upcoming_from_tmdb",
        side_effect=CommandError("TMDB unavailable"),
    )
    def test_upcoming_falls_back_to_cache_unless_refresh_was_requested(
        self,
        mocked_sync,
    ):
        content_id = self.insert_content(title="Premiera z cache")
        Content.objects.filter(pk=content_id).update(
            release_date=date.today() + timedelta(days=7),
            tmdb_refreshed_at=timezone.now() - timedelta(days=2),
        )

        cached_response = self.client.get(reverse("api:upcoming-contents"))
        refresh_response = self.client.get(
            reverse("api:upcoming-contents"),
            {"refresh": "1"},
        )

        self.assertEqual(cached_response.status_code, 200)
        self.assertEqual(cached_response.json()[0]["title"], "Premiera z cache")
        self.assertEqual(refresh_response.status_code, 503)
        self.assertEqual(
            refresh_response.json(),
            {"detail": "TMDB upcoming releases are unavailable."},
        )
        self.assertEqual(mocked_sync.call_count, 2)

    @patch("backend.api.views.sync_upcoming_from_tmdb")
    def test_upcoming_returns_only_future_movies_in_expected_order(
        self,
        mocked_sync,
    ):
        first_id = self.insert_content(2001, "Pierwsza")
        popular_id = self.insert_content(2002, "Popularniejsza tego samego dnia")
        less_popular_id = self.insert_content(2003, "Mniej popularna tego samego dnia")
        past_id = self.insert_content(2004, "Film archiwalny")
        tv_id = self.insert_content(2005, "Przyszły serial")
        fresh_at = timezone.now()
        Content.objects.filter(pk=first_id).update(
            release_date=date.today() + timedelta(days=1),
            popularity=10,
            tmdb_refreshed_at=fresh_at,
        )
        Content.objects.filter(pk=popular_id).update(
            release_date=date.today() + timedelta(days=2),
            popularity=90,
            tmdb_refreshed_at=fresh_at,
        )
        Content.objects.filter(pk=less_popular_id).update(
            release_date=date.today() + timedelta(days=2),
            popularity=20,
            tmdb_refreshed_at=fresh_at,
        )
        Content.objects.filter(pk=past_id).update(
            release_date=date.today() - timedelta(days=1),
            tmdb_refreshed_at=fresh_at,
        )
        Content.objects.filter(pk=tv_id).update(
            media_type="tv",
            release_date=date.today() + timedelta(days=1),
            tmdb_refreshed_at=fresh_at,
        )

        response = self.client.get(reverse("api:upcoming-contents"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["title"] for item in response.json()],
            [
                "Pierwsza",
                "Popularniejsza tego samego dnia",
                "Mniej popularna tego samego dnia",
            ],
        )
        mocked_sync.assert_not_called()
