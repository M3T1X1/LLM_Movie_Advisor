from django.test import SimpleTestCase
from django.urls import reverse


class FrontendRoutesTests(SimpleTestCase):
    routes = (
        "frontend-home",
        "frontend-login",
        "frontend-register",
        "frontend-forgot-password",
        "frontend-recommendations",
        "frontend-catalog",
        "frontend-trends",
        "frontend-upcoming",
        "frontend-watchlist",
        "frontend-analytics",
        "frontend-profile",
    )

    def test_frontend_routes_serve_the_vite_app(self):
        for route_name in self.routes:
            with self.subTest(route=route_name):
                response = self.client.get(reverse(route_name))

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, '<div id="root"></div>', html=True)

    def test_unknown_frontend_route_returns_not_found(self):
        response = self.client.get("/nie-istnieje")

        self.assertEqual(response.status_code, 404)

    def test_frontend_document_references_only_backend_static_prefix(self):
        response = self.client.get(reverse("frontend-home"))
        body = response.content.decode()

        self.assertIn('src="/static/frontend/', body)
        self.assertIn('href="/static/frontend/', body)
        self.assertNotIn("http://localhost:5173", body)

    def test_frontend_routes_return_html_with_security_headers(self):
        response = self.client.get(reverse("frontend-profile"))

        self.assertEqual(response.headers["Content-Type"], "text/html; charset=utf-8")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_frontend_routes_reject_post_requests(self):
        for route_name in self.routes:
            with self.subTest(route=route_name):
                response = self.client.post(reverse(route_name))
                self.assertEqual(response.status_code, 405)
                self.assertEqual(response.headers["Allow"], "GET, HEAD, OPTIONS")

    def test_api_route_is_not_shadowed_by_frontend_routes(self):
        response = self.client.get(reverse("accounts:session"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"authenticated": False, "user": None})
