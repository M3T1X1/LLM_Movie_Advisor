from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from backend.test import IN_MEMORY_TEST_CACHES


@override_settings(CACHES=IN_MEMORY_TEST_CACHES)
class AccountApiTestCase(TestCase):
    def setUp(self):
        self.password = "correct-horse-battery-staple"
        self.user = get_user_model().objects.create_user(
            username="tester",
            email="tester@example.com",
            password=self.password,
        )
