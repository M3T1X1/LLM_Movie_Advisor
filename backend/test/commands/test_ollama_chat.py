from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from backend.ollama import OllamaChatResponse, OllamaUnavailableError


class OllamaChatCommandTests(SimpleTestCase):
    @patch(
        "backend.accounts.management.commands.ollama_chat.get_ollama_client"
    )
    def test_sends_prompt_to_downloaded_model(self, mocked_get_client):
        client = mocked_get_client.return_value
        client.model = "llama3.1:8b"
        client.has_configured_model.return_value = True
        client.chat.return_value = OllamaChatResponse(
            content="Polecam testowy thriller.",
            model="llama3.1:8b",
            done_reason="stop",
            total_duration_ns=100,
            prompt_eval_count=20,
            eval_count=7,
        )
        stdout = StringIO()
        stderr = StringIO()

        call_command(
            "ollama_chat",
            "Poleć",
            "thriller",
            stdout=stdout,
            stderr=stderr,
        )

        self.assertEqual(stdout.getvalue().strip(), "Polecam testowy thriller.")
        self.assertIn("prompt_tokens=20", stderr.getvalue())
        messages = client.chat.call_args.args[0]
        self.assertEqual(messages[-1], {"role": "user", "content": "Poleć thriller"})
        self.assertEqual(messages[0]["role"], "system")

    @patch(
        "backend.accounts.management.commands.ollama_chat.get_ollama_client"
    )
    def test_reports_missing_configured_model(self, mocked_get_client):
        client = mocked_get_client.return_value
        client.model = "missing-model"
        client.has_configured_model.return_value = False

        with self.assertRaisesMessage(CommandError, "is not downloaded"):
            call_command("ollama_chat", "Test")

        client.chat.assert_not_called()

    @patch(
        "backend.accounts.management.commands.ollama_chat.get_ollama_client"
    )
    def test_converts_connection_failure_to_command_error(self, mocked_get_client):
        client = mocked_get_client.return_value
        client.has_configured_model.side_effect = OllamaUnavailableError(
            "Ollama service is unavailable."
        )

        with self.assertRaisesMessage(CommandError, "service is unavailable"):
            call_command("ollama_chat", "Test")
