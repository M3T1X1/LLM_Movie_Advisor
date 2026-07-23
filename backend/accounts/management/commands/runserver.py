import os
import subprocess
import sys

from django.conf import settings
from django.contrib.staticfiles.management.commands.runserver import (
    Command as DjangoRunserverCommand,
)
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection


class Command(DjangoRunserverCommand):
    help = (
        "Starts the development server after running backend tests and seeding "
        "an empty business database."
    )

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--skip-bootstrap",
            action="store_true",
            help="Start the server without running startup tests or automatic seeding.",
        )

    def handle(self, *args, **options):
        skip_bootstrap = options.pop("skip_bootstrap", False)
        is_autoreload_child = os.environ.get("RUN_MAIN") == "true"

        if not skip_bootstrap and not is_autoreload_child:
            self._bootstrap()

        return super().handle(*args, **options)

    def _bootstrap(self):
        if not settings.DEBUG:
            raise CommandError(
                "Automatic tests and demo seeding are available only when DEBUG=True."
            )

        self.stdout.write("Running backend tests before server startup...")
        self._run_tests()
        self.stdout.write(self.style.SUCCESS("Backend tests passed."))

        if self._database_needs_seed():
            self.stdout.write("Business database is empty. Running seed_demo_data...")
            call_command("seed_demo_data", stdout=self.stdout, stderr=self.stderr)
        else:
            self.stdout.write("Business database already contains content. Skipping seeder.")

    def _run_tests(self):
        result = subprocess.run(
            [sys.executable, "manage.py", "test"],
            cwd=settings.BASE_DIR,
            check=False,
        )
        if result.returncode:
            raise CommandError(
                "Backend tests failed. The development server was not started."
            )

    def _database_needs_seed(self) -> bool:
        table_names = set(connection.introspection.table_names())
        if "content" not in table_names:
            raise CommandError(
                "The business database schema is missing. Apply "
                "`przydatne/postgresql_recommendation_platform_schema.sql` first."
            )

        with connection.cursor() as cursor:
            cursor.execute("SELECT EXISTS (SELECT 1 FROM content LIMIT 1)")
            return not cursor.fetchone()[0]
