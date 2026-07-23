import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import connection
from django.db import transaction


class Command(BaseCommand):
    help = "Creates or updates development seed data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default=os.environ.get("SEED_USER_USERNAME", "demo"),
            help="Demo account username (default: demo).",
        )
        parser.add_argument(
            "--email",
            default=os.environ.get("SEED_USER_EMAIL", "demo@example.com"),
            help="Demo account email (default: demo@example.com).",
        )
        parser.add_argument(
            "--password",
            default=os.environ.get("SEED_USER_PASSWORD"),
            help="Demo password. Prefer setting SEED_USER_PASSWORD in the environment.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Seed data can only be loaded when DEBUG=True.")

        username = options["username"].strip()
        email = options["email"].strip().lower()
        password = options["password"]

        if not username:
            raise CommandError("Username cannot be empty.")
        if not password:
            raise CommandError(
                "Password is required. Use --password or SEED_USER_PASSWORD."
            )

        try:
            validate_email(email)
        except ValidationError as error:
            raise CommandError("A valid email address is required.") from error

        user_model = get_user_model()
        if user_model._meta.db_table not in connection.introspection.table_names():
            raise CommandError(
                "Database tables are missing. Run `python manage.py migrate` first."
            )

        user = user_model.objects.filter(username=username).first()
        created = user is None
        if created:
            user = user_model(username=username, email=email)
        else:
            user.email = email

        try:
            validate_password(password, user=user)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error

        user.set_password(password)
        user.full_clean()
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(f"{action} demo user: {user.email} ({user.username})")
        )
