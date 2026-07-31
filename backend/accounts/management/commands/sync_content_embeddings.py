from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from backend.embeddings import EmbeddingSyncResult, sync_content_embeddings
from backend.ollama import OllamaError, get_ollama_client
from backend.redis import EMBEDDING_SYNC_LOCK_KEY, run_with_redis_lock


class Command(BaseCommand):
    help = (
        "Generates missing or stale catalog embeddings with Ollama and stores "
        "them in PostgreSQL/pgvector."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=settings.LLM_EMBEDDING_BATCH_SIZE,
            help="Number of catalog texts sent to Ollama in one request.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Maximum number of catalog records examined in this run.",
        )
        parser.add_argument(
            "--content-id",
            type=int,
            action="append",
            dest="content_ids",
            help="Generate an embedding only for this content ID (repeatable).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Regenerate embeddings even when the source hash is unchanged.",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        limit = options.get("limit")
        content_ids = options.get("content_ids")
        if not 1 <= batch_size <= 256:
            raise CommandError("--batch-size must be between 1 and 256.")
        if limit is not None and limit < 1:
            raise CommandError("--limit must be greater than zero.")
        if content_ids and any(content_id < 1 for content_id in content_ids):
            raise CommandError("--content-id must be greater than zero.")

        client = get_ollama_client()
        try:
            if not client.has_configured_embedding_model():
                raise CommandError(
                    f"Ollama embedding model `{client.embedding_model}` "
                    "is not downloaded."
                )
        except OllamaError as error:
            raise CommandError(str(error)) from error

        result: EmbeddingSyncResult | None = None

        def synchronize() -> None:
            nonlocal result
            result = sync_content_embeddings(
                content_ids=content_ids,
                batch_size=batch_size,
                force=options["force"],
                limit=limit,
                client=client,
            )

        try:
            executed = run_with_redis_lock(
                EMBEDDING_SYNC_LOCK_KEY,
                synchronize,
                timeout=settings.LLM_EMBEDDING_SYNC_LOCK_TIMEOUT,
            )
        except (OllamaError, ValueError) as error:
            raise CommandError(str(error)) from error

        if not executed:
            self.stdout.write(
                self.style.WARNING(
                    "Embedding synchronization skipped because another run "
                    "is active."
                )
            )
            return
        if result is None:
            raise CommandError("Embedding synchronization returned no result.")
        self.stdout.write(
            self.style.SUCCESS(
                "Embedding synchronization finished: "
                f"examined={result.examined}, generated={result.generated}, "
                f"created={result.created}, updated={result.updated}, "
                f"skipped={result.skipped}."
            )
        )
