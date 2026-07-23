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
