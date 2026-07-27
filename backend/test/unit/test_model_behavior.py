from django.test import SimpleTestCase

from backend.api.models import (
    AgentExecution,
    BusinessUser,
    Conversation,
    RecommendationRun,
    RunCandidate,
)
from backend.api.views import json_object


class ModelBehaviorTests(SimpleTestCase):
    def test_model_string_representations(self):
        self.assertEqual(
            str(BusinessUser(username="tester")),
            "tester",
        )
        self.assertEqual(
            str(Conversation(pk=7, title="Wieczorny film")),
            "Wieczorny film",
        )
        self.assertEqual(str(Conversation(pk=7)), "Rozmowa 7")

    def test_workflow_models_have_expected_default_statuses(self):
        self.assertEqual(RecommendationRun().status, "pending")
        self.assertEqual(RunCandidate().status, "pending")
        self.assertEqual(AgentExecution().status, "pending")

    def test_json_object_accepts_legacy_object_text_and_rejects_other_shapes(self):
        self.assertEqual(json_object({"source": "jsonb"}), {"source": "jsonb"})
        self.assertEqual(
            json_object('{"source": "legacy-text"}'),
            {"source": "legacy-text"},
        )
        for value in ("invalid-json", "[]", [], None, 123):
            with self.subTest(value=value):
                self.assertEqual(json_object(value), {})

