import signal
import time

from django.core.management.base import BaseCommand
from django.db import connection, close_old_connections

from backend.api.models import UserProfile
from backend.semantic_profile import refresh_profile


class Command(BaseCommand):
    help = 'Rebuild changed semantic profiles in the background; --once scans once.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true')
        parser.add_argument('--interval', type=int, default=10)

    def handle(self, *args, **options):
        stopping = False

        def stop(*_):
            nonlocal stopping
            stopping = True

        previous = {s: signal.signal(s, stop) for s in (signal.SIGTERM, signal.SIGINT)}
        try:
            while not stopping:
                close_old_connections()
                # PostgreSQL session lock: no duplicate work across worker replicas.
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_try_advisory_lock(%s)', [70421631])
                    acquired = cursor.fetchone()[0]
                if acquired:
                    try:
                        ids = UserProfile.objects.filter(user__is_active=True).values_list('user_id', flat=True)
                        for user_id in ids.iterator(chunk_size=100):
                            if stopping:
                                break
                            try:
                                result = refresh_profile(user_id)
                                if result in {'rebuilt', 'failed'}:
                                    self.stdout.write(f'Profile {user_id}: {result}')
                            except UserProfile.DoesNotExist:
                                pass  # Account removed during this scan.
                    finally:
                        with connection.cursor() as cursor:
                            cursor.execute('SELECT pg_advisory_unlock(%s)', [70421631])
                if options['once']:
                    break
                for _ in range(max(1, options['interval'])):
                    if stopping:
                        break
                    time.sleep(1)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
