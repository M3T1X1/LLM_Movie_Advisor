from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from backend.embeddings import EmbeddingSyncResult


class SyncContentEmbeddingsCommandTests(SimpleTestCase):
    @patch(
        "backend.accounts.management.commands.sync_content_embeddings."
        "run_with_redis_lock",
        side_effect=lambda key, operation, **kwargs: operation() or True,
    )
    @patch(
        "backend.accounts.management.commands.sync_content_embeddings."
        "sync_content_embeddings",
        return_value=EmbeddingSyncResult(3, 2, 1, 1, 1),
    )
    @patch(
        "backend.accounts.management.commands.sync_content_embeddings."
        "get_ollama_client"
    )
    def test_generates_only_selected_embeddings(
        self,
        mocked_get_client,
        mocked_sync,
        mocked_lock,
    ):
        client = mocked_get_client.return_value
        client.has_configured_embedding_model.return_value = True
        stdout = StringIO()

        call_command(
            "sync_content_embeddings",
            "--batch-size",
            "16",
            "--content-id",
            "3",
            "--content-id",
            "5",
            stdout=stdout,
        )

        mocked_sync.assert_called_once_with(
            content_ids=[3, 5],
            batch_size=16,
            force=False,
            limit=None,
            client=client,
        )
        self.assertIn("generated=2", stdout.getvalue())
        mocked_lock.assert_called_once()

    @patch(
        "backend.accounts.management.commands.sync_content_embeddings."
        "get_ollama_client"
    )
    def test_rejects_missing_embedding_model(self, mocked_get_client):
        client = mocked_get_client.return_value
        client.embedding_model = "missing-embedding-model"
        client.has_configured_embedding_model.return_value = False

        with self.assertRaisesMessage(CommandError, "is not downloaded"):
            call_command("sync_content_embeddings")

    def test_rejects_invalid_batch_size(self):
        with self.assertRaisesMessage(CommandError, "between 1 and 256"):
            call_command("sync_content_embeddings", "--batch-size", "0")
