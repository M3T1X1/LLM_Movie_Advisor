import json

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.urls import reverse

from backend.accounts.services import sync_business_user
from backend.api.models import (
    Content,
    Conversation,
    Interaction,
    Message,
)
from backend.test.integration.api_base import ApiIntegrationTestCase


class InteractionValidationApiTests(ApiIntegrationTestCase):
    def test_interaction_create_deduplicate_and_delete(self):
        content_id = self.insert_content()
        payload = {
            "content_id": str(content_id),
            "source_candidate_id": None,
            "interaction_type": "watchlisted",
            "rating": None,
            "metadata": {},
        }

        first = self.client.post(
            reverse("api:interactions"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        second = self.client.post(
            reverse("api:interactions"),
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["id"], second.json()["id"])
        delete_response = self.client.delete(
            reverse(
                "api:interaction-detail",
                kwargs={"interaction_id": first.json()["id"]},
            )
        )
        self.assertEqual(delete_response.status_code, 204)

    def test_interactions_validate_identifiers_type_rating_and_metadata(self):
        content_id = self.insert_content()
        invalid_payloads = (
            {
                "content_id": 999999,
                "interaction_type": "liked",
            },
            {
                "content_id": content_id,
                "source_candidate_id": 999999,
                "interaction_type": "liked",
            },
            {
                "content_id": content_id,
                "interaction_type": "shared",
            },
            {
                "content_id": content_id,
                "interaction_type": "rated",
                "rating": -1,
            },
            {
                "content_id": content_id,
                "interaction_type": "rated",
                "rating": 11,
            },
        )

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    reverse("api:interactions"),
                    data=json.dumps(payload),
                    content_type="application/json",
                )
                self.assertIn(response.status_code, (400, 404))
                self.assertIn("detail", response.json())

        metadata_response = self.client.post(
            reverse("api:interactions"),
            data=json.dumps(
                {
                    "content_id": content_id,
                    "interaction_type": "liked",
                    "rating": 9,
                    "metadata": ["not", "an", "object"],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(metadata_response.status_code, 201)
        self.assertIsNone(metadata_response.json()["rating"])
        self.assertEqual(metadata_response.json()["metadata"], {})

    def test_rated_interaction_rejects_boolean_rating(self):
        content_id = self.insert_content()

        response = self.client.post(
            reverse("api:interactions"),
            data=json.dumps(
                {
                    "content_id": content_id,
                    "interaction_type": "rated",
                    "rating": True,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())

    def test_source_candidate_must_belong_to_current_user(self):
        content_id = self.insert_content()
        other_user = get_user_model().objects.create_user(
            username="candidate-owner",
            email="candidate-owner@example.com",
            password=self.password,
        )
        other_business_id = int(sync_business_user(other_user)["id"])
        candidate = self.create_recommendation_candidate(
            user_id=other_business_id,
            content_id=content_id,
        )

        response = self.client.post(
            reverse("api:interactions"),
            data=json.dumps(
                {
                    "content_id": content_id,
                    "source_candidate_id": candidate.pk,
                    "interaction_type": "liked",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("detail", response.json())
        self.assertFalse(
            Interaction.objects.filter(
                user_id=self.business_user_id,
                source_candidate=candidate,
            ).exists()
        )

    def test_source_candidate_must_match_content_and_valid_candidate_is_accepted(self):
        candidate_content_id = self.insert_content(6301, "Kandydat")
        other_content_id = self.insert_content(6302, "Inna treść")
        candidate = self.create_recommendation_candidate(
            content_id=candidate_content_id
        )

        mismatch = self.client.post(
            reverse("api:interactions"),
            data=json.dumps(
                {
                    "content_id": other_content_id,
                    "source_candidate_id": candidate.pk,
                    "interaction_type": "liked",
                }
            ),
            content_type="application/json",
        )
        valid = self.client.post(
            reverse("api:interactions"),
            data=json.dumps(
                {
                    "content_id": candidate_content_id,
                    "source_candidate_id": candidate.pk,
                    "interaction_type": "liked",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(mismatch.status_code, 404)
        self.assertEqual(valid.status_code, 201)
        self.assertEqual(valid.json()["sourceCandidateId"], str(candidate.pk))

    def test_interaction_json_identifier_and_rating_boundaries(self):
        content_id = self.insert_content()
        invalid_payloads = (
            "{",
            json.dumps([]),
            json.dumps({}),
            json.dumps({"content_id": True, "interaction_type": "liked"}),
            json.dumps(
                {
                    "content_id": content_id,
                    "interaction_type": "rated",
                    "rating": "8",
                }
            ),
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.client.post(
                    reverse("api:interactions"),
                    data=payload,
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 400)

        for rating in (0, 8.5, 10):
            with self.subTest(rating=rating):
                response = self.client.post(
                    reverse("api:interactions"),
                    data=json.dumps(
                        {
                            "content_id": content_id,
                            "interaction_type": "rated",
                            "rating": rating,
                        }
                    ),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json()["rating"], rating)
