from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

from django.test import override_settings
from django.utils import timezone

from backend.api.models import Genre, Interaction, UserPreference, UserProfile
from backend.semantic_profile import refresh_profile, source_snapshot, evidence
from backend.test.integration.api_base import ApiIntegrationTestCase


@override_settings(SEMANTIC_PROFILE_DEBOUNCE_SECONDS=15, SEMANTIC_PROFILE_RETRY_SECONDS=300)
class SemanticProfileTests(ApiIntegrationTestCase):
    def preference(self, value='Humor', polarity=1, kind='humor'):
        return UserPreference.objects.create(user_id=self.business_user_id,
            preference_type=kind, preference_value=value, polarity=polarity)

    def signals(self, interaction_type='liked'):
        genre = Genre.objects.create(tmdb_genre_id=53, name='Thriller')
        for index in range(2):
            content_id = self.insert_content(tmdb_id=1001 + index)
            genre.contents.add(content_id)
            Interaction.objects.create(user_id=self.business_user_id, content_id=content_id,
                                       interaction_type=interaction_type)

    def rebuild(self, client=None):
        now = timezone.now()
        self.assertEqual(refresh_profile(self.business_user_id, now=now, client=client), 'pending')
        return refresh_profile(self.business_user_id, now=now + timedelta(seconds=16), client=client)

    def test_explicit_preferences_build_without_inference_and_are_consumed(self):
        from backend.api.models import BusinessUser
        from backend.recommendation_agents.profiling import build_profiling_input
        self.preference()
        client = Mock()
        self.assertEqual(self.rebuild(client), 'rebuilt')
        profile = UserProfile.objects.get(user_id=self.business_user_id)
        self.assertEqual(profile.semantic_summary, 'Lubi: Humor.')
        self.assertIsNotNone(profile.last_rebuilt_at)
        self.assertEqual(refresh_profile(self.business_user_id), 'unchanged')
        client.chat.assert_not_called()
        value = build_profiling_input(BusinessUser.objects.get(pk=self.business_user_id), 'Poleć film')
        self.assertEqual(value.semantic_profile, profile.semantic_summary)

    def test_model_selects_only_supported_repeated_taste(self):
        self.signals()
        client = Mock()
        client.chat.return_value = SimpleNamespace(content='{"selected":[0]}')
        self.assertEqual(self.rebuild(client), 'rebuilt')
        self.assertIn('pozytywne oceny gatunku: Thriller', UserProfile.objects.get(
            user_id=self.business_user_id).semantic_summary)

    def test_invalid_model_keeps_old_profile_and_retries(self):
        self.signals()
        UserProfile.objects.filter(user_id=self.business_user_id).update(semantic_summary='Poprzedni gust')
        client = Mock()
        client.chat.return_value = SimpleNamespace(content='{"selected":[99]}')
        self.assertEqual(self.rebuild(client), 'failed')
        profile = UserProfile.objects.get(user_id=self.business_user_id)
        self.assertEqual(profile.semantic_summary, 'Poprzedni gust')
        self.assertEqual(refresh_profile(self.business_user_id, client=client), 'pending')
        self.assertEqual(client.chat.call_count, 1)

    def test_change_during_inference_does_not_publish_stale_result(self):
        self.signals()
        client = Mock()
        def change(*args, **kwargs):
            self.preference()
            return SimpleNamespace(content='{"selected":[0]}')
        client.chat.side_effect = change
        self.assertEqual(self.rebuild(client), 'superseded')
        self.assertIsNone(UserProfile.objects.get(user_id=self.business_user_id).semantic_summary)

    def test_fast_changes_restart_debounce(self):
        self.preference()
        now = timezone.now()
        self.assertEqual(refresh_profile(self.business_user_id, now=now), 'pending')
        self.preference('Gore', -1, 'violence')
        self.assertEqual(refresh_profile(self.business_user_id, now=now+timedelta(seconds=16)), 'pending')
        self.assertEqual(refresh_profile(self.business_user_id, now=now+timedelta(seconds=32)), 'rebuilt')

    def test_watched_and_watchlist_are_not_positive_taste(self):
        self.signals('watched')
        self.assertEqual(evidence(source_snapshot(self.business_user_id)), ([], []))
        self.assertEqual(self.rebuild(Mock()), 'rebuilt')
        self.assertIsNone(UserProfile.objects.get(user_id=self.business_user_id).semantic_summary)

    def test_explicit_dislike_overrides_inferred_genre_preference(self):
        self.signals()
        self.preference('Thriller', -1, 'genre')
        self.assertEqual(evidence(source_snapshot(self.business_user_id)), (['Unika: Thriller.'], []))

    def test_removing_preferences_rebuilds_without_old_facts(self):
        self.preference()
        self.assertEqual(self.rebuild(), 'rebuilt')
        UserPreference.objects.filter(user_id=self.business_user_id).delete()
        self.assertEqual(self.rebuild(), 'rebuilt')
        self.assertIsNone(UserProfile.objects.get(user_id=self.business_user_id).semantic_summary)

    def test_reverting_then_reapplying_change_restarts_debounce(self):
        pref = self.preference()
        self.assertEqual(self.rebuild(), 'rebuilt')
        now = timezone.now() + timedelta(seconds=20)
        pref.polarity = -1
        pref.save()
        self.assertEqual(refresh_profile(self.business_user_id, now=now), 'pending')
        pref.polarity = 1
        pref.save()
        self.assertEqual(refresh_profile(self.business_user_id, now=now+timedelta(seconds=20)), 'unchanged')
        pref.polarity = -1
        pref.save()
        self.assertEqual(refresh_profile(self.business_user_id, now=now+timedelta(seconds=40)), 'pending')

    def test_empty_selection_cannot_silently_discard_supported_taste(self):
        self.signals()
        UserProfile.objects.filter(user_id=self.business_user_id).update(semantic_summary='Poprzedni gust')
        client = Mock()
        client.chat.return_value = SimpleNamespace(content='{"selected":[]}')
        self.assertEqual(self.rebuild(client), 'failed')
        profile = UserProfile.objects.get(user_id=self.business_user_id)
        self.assertEqual(profile.semantic_summary, 'Poprzedni gust')
        self.assertEqual(profile.semantic_source_hash, '')
