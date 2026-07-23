from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


CONFIRMATION_TEXT = "USUN DANE"

BUSINESS_TABLES = (
    "agent_execution",
    "interaction",
    "run_candidate",
    "content_embedding",
    "content_genre",
    "genre",
    "content",
    "recommendation_run",
    "recommendation_request",
    "message",
    "conversation",
    "user_preference",
    "user_profile",
    "app_user",
)

USER_TABLES = {
    "app_user",
    "user_profile",
    "user_preference",
}


class Command(BaseCommand):
    help = (
        "Removes application data from PostgreSQL without deleting the schema "
        "or Django migration history."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip the interactive confirmation.",
        )
        parser.add_argument(
            "--keep-users",
            action="store_true",
            help=(
                "Keep Django accounts, app_user records, profiles and preferences. "
                "Active sessions are still removed."
            ),
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Database clearing is available only when DEBUG=True."
            )

        keep_users = options["keep_users"]
        if not options["yes"] and not self._confirmed(keep_users):
            self.stdout.write(self.style.WARNING("Database clearing cancelled."))
            return

        tables = self._target_tables(keep_users)
        self._validate_schema(tables)
        self._truncate(tables)

        scope = (
            "Application data removed; user accounts, profiles and preferences kept."
            if keep_users
            else "All application data, user accounts and sessions removed."
        )
        self.stdout.write(self.style.SUCCESS(scope))
        self.stdout.write(
            "Database schema and Django migration history were not changed."
        )

    def _confirmed(self, keep_users: bool) -> bool:
        scope = (
            "all application data except accounts, profiles and preferences"
            if keep_users
            else "all application data, accounts and sessions"
        )
        self.stdout.write(self.style.WARNING(f"This will permanently remove {scope}."))
        response = input(f'Type "{CONFIRMATION_TEXT}" to continue: ')
        return response.strip() == CONFIRMATION_TEXT

    def _target_tables(self, keep_users: bool) -> tuple[str, ...]:
        business_tables = tuple(
            table
            for table in BUSINESS_TABLES
            if not keep_users or table not in USER_TABLES
        )
        django_tables = (
            ("django_session",)
            if keep_users
            else ("django_session", "auth_user")
        )
        return business_tables + django_tables

    def _validate_schema(self, tables: tuple[str, ...]):
        existing_tables = set(connection.introspection.table_names())
        missing_tables = sorted(set(tables) - existing_tables)
        if missing_tables:
            raise CommandError(
                "Cannot clear the database because required tables are missing: "
                + ", ".join(missing_tables)
            )

    @transaction.atomic
    def _truncate(self, tables: tuple[str, ...]):
        quoted_tables = ", ".join(
            connection.ops.quote_name(table) for table in tables
        )
        with connection.cursor() as cursor:
            cursor.execute(
                f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY CASCADE"
            )
