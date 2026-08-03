import json

from django.test import Client
from django.urls import reverse

from backend.api.models import Conversation, Interaction
from backend.test.integration.api_base import ApiIntegrationTestCase


class ApiAccessControlTests(ApiIntegrationTestCase):
    def test_resources_require_authentication(self):
        self.client.logout()
        protected_requests = (
            ("get", reverse("api:bootstrap")),
            ("get", reverse("api:contents")),
            ("get", reverse("api:conversations")),
            ("post", reverse("api:chat")),
            ("post", reverse("api:interactions")),
            ("post", reverse("api:profile-preferences")),
            ("delete", reverse("api:profile-preferences")),
        )

        for method, url in protected_requests:
            with self.subTest(method=method, url=url):
                if method == "post":
                    response = self.client.post(
                        url,
                        data="{}",
                        content_type="application/json",
                    )
                else:
                    response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(
                    response.json()["detail"],
                    "Authentication required.",
                )

    def test_business_api_rejects_wrong_http_methods(self):
        conversation_id = self.client.post(
            reverse("api:conversations"),
            data="{}",
            content_type="application/json",
        ).json()["id"]
        cases = (
            ("post", reverse("api:health")),
            ("get", reverse("api:chat")),
            ("post", reverse("api:bootstrap")),
            ("post", reverse("api:contents")),
            ("post", reverse("api:upcoming-contents")),
            ("post", reverse("api:trends")),
            ("get", reverse("api:profile")),
            ("patch", reverse("api:profile-preferences")),
            (
                "put",
                reverse(
                    "api:conversation-detail",
                    kwargs={"conversation_id": conversation_id},
                ),
            ),
            (
                "get",
                reverse(
                    "api:conversation-messages",
                    kwargs={"conversation_id": conversation_id},
                ),
            ),
            ("get", reverse("api:interactions")),
        )
        for method, url in cases:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, 405)
                self.assertIn("Allow", response.headers)

    def test_business_api_mutations_require_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        conversation_id = Conversation.objects.create(
            user_id=self.business_user_id
        ).pk
        content_id = self.insert_content()
        interaction = Interaction.objects.create(
            user_id=self.business_user_id,
            content_id=content_id,
            interaction_type="liked",
        )
        cases = (
            (
                "patch",
                reverse("api:profile"),
                {"username": "csrf", "email": "csrf@example.com"},
            ),
            ("delete", reverse("api:profile-preferences"), None),
            (
                "post",
                reverse("api:profile-preferences"),
                {"preferences": []},
            ),
            ("post", reverse("api:conversations"), {}),
            ("post", reverse("api:chat"), {"message": "CSRF"}),
            (
                "patch",
                reverse(
                    "api:conversation-detail",
                    kwargs={"conversation_id": conversation_id},
                ),
                {"title": "CSRF"},
            ),
            (
                "delete",
                reverse(
                    "api:conversation-detail",
                    kwargs={"conversation_id": conversation_id},
                ),
                None,
            ),
            (
                "post",
                reverse(
                    "api:conversation-messages",
                    kwargs={"conversation_id": conversation_id},
                ),
                {"content": "CSRF"},
            ),
            (
                "post",
                reverse("api:interactions"),
                {"content_id": content_id, "interaction_type": "liked"},
            ),
            (
                "delete",
                reverse(
                    "api:interaction-detail",
                    kwargs={"interaction_id": interaction.pk},
                ),
                None,
            ),
        )
        for method, url, payload in cases:
            with self.subTest(method=method, url=url):
                kwargs = (
                    {
                        "data": json.dumps(payload),
                        "content_type": "application/json",
                    }
                    if payload is not None
                    else {}
                )
                response = getattr(csrf_client, method)(url, **kwargs)
                self.assertEqual(response.status_code, 403)
