from django.contrib.auth import get_user_model
from django.test import TestCase


class AccountApiTestCase(TestCase):
    def setUp(self):
        self.password = "correct-horse-battery-staple"
        self.user = get_user_model().objects.create_user(
            username="tester",
            email="tester@example.com",
            password=self.password,
        )
