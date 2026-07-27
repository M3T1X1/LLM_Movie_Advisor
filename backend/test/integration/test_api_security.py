import json

from django.db import connection
from django.urls import reverse

from backend.api.models import BusinessUser, Content, Message
from backend.test.integration.api_base import ApiIntegrationTestCase


class ApiSecurityTests(ApiIntegrationTestCase):
    def test_api_query_parameters_resist_sql_injection(self):
        content_id = self.insert_content(6701, "Bezpieczny rekord")
        sql_payload = "' OR 1=1; DROP TABLE content; --"
        cases = (
            {"q": sql_payload},
            {"genre": sql_payload},
            {"ids": "1); DROP TABLE content; --"},
            {"min_rating": "0 OR 1=1"},
            {"year_from": "2026; DROP TABLE content"},
            {"sort": "title; DROP TABLE content"},
        )

        for query in cases:
            with self.subTest(query=query):
                response = self.client.get(reverse("api:contents"), query)
                self.assertIn(response.status_code, (200, 400))
                if response.status_code == 400:
                    self.assertIn("detail", response.json())

        self.assertTrue(Content.objects.filter(pk=content_id).exists())
        with connection.cursor() as cursor:
            self.assertIn("content", connection.introspection.table_names(cursor))

    def test_write_endpoints_store_xss_as_data_and_reject_sqli_profile_values(self):
        xss_payload = (
            '<img src=x onerror="window.__xss=true">'
            "<script>window.__xss=true</script>"
        )
        sql_payload = "attacker', is_active=false; DROP TABLE app_user; --"
        conversation_id = self.client.post(
            reverse("api:conversations"),
            data="{}",
            content_type="application/json",
        ).json()["id"]
        message_response = self.client.post(
            reverse(
                "api:conversation-messages",
                kwargs={"conversation_id": conversation_id},
            ),
            data=json.dumps({"content": xss_payload}),
            content_type="application/json",
        )
        profile_response = self.client.patch(
            reverse("api:profile"),
            data=json.dumps(
                {
                    "username": sql_payload,
                    "email": "safe@example.com",
                }
            ),
            content_type="application/json",
        )
        content_id = self.insert_content(6702, "XSS metadata")
        interaction_response = self.client.post(
            reverse("api:interactions"),
            data=json.dumps(
                {
                    "content_id": content_id,
                    "interaction_type": "liked",
                    "metadata": {"untrusted": xss_payload},
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(message_response.status_code, 201)
        self.assertEqual(message_response["Content-Type"], "application/json")
        self.assertEqual(message_response.json()["content"], xss_payload)
        self.assertEqual(
            Message.objects.get(
                conversation_id=conversation_id,
                sequence_no=1,
            ).content,
            xss_payload,
        )
        self.assertEqual(profile_response.status_code, 400)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "api-user")
        self.assertEqual(interaction_response.status_code, 201)
        self.assertEqual(
            interaction_response.json()["metadata"]["untrusted"],
            xss_payload,
        )
        self.assertTrue(BusinessUser.objects.filter(pk=self.business_user_id).exists())

    def test_admin_escapes_stored_xss_and_search_resists_sql_injection(self):
        xss_payload = '<script>window.__adminXss=true</script>'
        content_id = self.insert_content(6703, xss_payload)
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_login(self.user)

        change_response = self.client.get(
            reverse("admin:api_content_change", args=[content_id])
        )
        search_response = self.client.get(
            reverse("admin:api_content_changelist"),
            {"q": "' UNION SELECT password FROM auth_user --"},
        )

        self.assertEqual(change_response.status_code, 200)
        self.assertNotContains(change_response, xss_payload)
        self.assertContains(
            change_response,
            "&lt;script&gt;window.__adminXss=true&lt;/script&gt;",
            html=False,
        )
        self.assertEqual(search_response.status_code, 200)
        self.assertTrue(Content.objects.filter(pk=content_id).exists())
