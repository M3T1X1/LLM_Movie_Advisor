import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from django.test import SimpleTestCase

from backend.ollama import (
    OllamaClient,
    OllamaConfigurationError,
    OllamaResponseError,
    OllamaUnavailableError,
)


class OllamaClientTests(SimpleTestCase):
    def setUp(self):
        self.client = OllamaClient(
            base_url="http://ollama:11434/",
            model="llama3.1:8b",
            request_timeout=120,
            health_timeout=2,
        )

    def test_rejects_invalid_connection_configuration(self):
        invalid_options = (
            {
                "base_url": "",
                "model": "model",
                "request_timeout": 120,
                "health_timeout": 2,
            },
            {
                "base_url": "http://ollama:11434",
                "model": " ",
                "request_timeout": 120,
                "health_timeout": 2,
            },
            {
                "base_url": "http://ollama:11434",
                "model": "model",
                "request_timeout": 0,
                "health_timeout": 2,
            },
        )

        for options in invalid_options:
            with self.subTest(options=options):
                with self.assertRaises(OllamaConfigurationError):
                    OllamaClient(**options)

    @staticmethod
    def response(payload):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            payload
        ).encode("utf-8")
        return response

    @patch("backend.ollama.urlopen")
    def test_lists_models_with_short_health_timeout(self, mocked_urlopen):
        mocked_urlopen.return_value = self.response(
            {
                "models": [
                    {"name": "llama3.1:8b"},
                    {"model": "embedding-model:latest"},
                ]
            }
        )

        models = self.client.list_models()

        self.assertEqual(
            models,
            ("llama3.1:8b", "embedding-model:latest"),
        )
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://ollama:11434/api/tags")
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(mocked_urlopen.call_args.kwargs["timeout"], 2)

    def test_accepts_implicit_latest_model_tag(self):
        client = OllamaClient(
            base_url="http://ollama:11434",
            model="local-model",
            request_timeout=120,
            health_timeout=2,
        )
        client.list_models = MagicMock(return_value=("local-model:latest",))

        self.assertTrue(client.has_configured_model())

    @patch("backend.ollama.urlopen")
    def test_sends_non_streaming_chat_and_returns_metrics(self, mocked_urlopen):
        mocked_urlopen.return_value = self.response(
            {
                "model": "llama3.1:8b",
                "message": {
                    "role": "assistant",
                    "content": "Polecam film testowy.",
                },
                "done": True,
                "done_reason": "stop",
                "total_duration": 123456,
                "prompt_eval_count": 21,
                "eval_count": 8,
            }
        )

        result = self.client.chat(
            [{"role": "user", "content": "  Poleć mi film.  "}],
            response_format={"type": "object"},
            options={"temperature": 0},
        )

        self.assertEqual(result.content, "Polecam film testowy.")
        self.assertEqual(result.model, "llama3.1:8b")
        self.assertEqual(result.done_reason, "stop")
        self.assertEqual(result.total_duration_ns, 123456)
        self.assertEqual(result.prompt_eval_count, 21)
        self.assertEqual(result.eval_count, 8)

        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://ollama:11434/api/chat")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(mocked_urlopen.call_args.kwargs["timeout"], 120)
        self.assertEqual(
            json.loads(request.data.decode("utf-8")),
            {
                "model": "llama3.1:8b",
                "messages": [{"role": "user", "content": "Poleć mi film."}],
                "stream": False,
                "format": {"type": "object"},
                "options": {"temperature": 0},
            },
        )

    def test_rejects_empty_or_unsupported_messages_before_http_request(self):
        invalid_messages = (
            [],
            [{"role": "tool", "content": "wynik"}],
            [{"role": "user", "content": "  "}],
        )

        for messages in invalid_messages:
            with self.subTest(messages=messages):
                with self.assertRaises(ValueError):
                    self.client.chat(messages)

    @patch("backend.ollama.urlopen")
    def test_reports_unavailable_service_without_leaking_transport_error(
        self,
        mocked_urlopen,
    ):
        mocked_urlopen.side_effect = URLError("tajny adres")

        with self.assertRaisesMessage(
            OllamaUnavailableError,
            "Ollama service is unavailable",
        ) as context:
            self.client.list_models()

        self.assertNotIn("tajny adres", str(context.exception))

    @patch("backend.ollama.urlopen")
    def test_reports_http_error_without_returning_response_body(
        self,
        mocked_urlopen,
    ):
        mocked_urlopen.side_effect = HTTPError(
            "http://ollama:11434/api/chat",
            404,
            "Not Found",
            {},
            BytesIO(b'{"error": "tajna odpowiedz"}'),
        )

        with self.assertRaisesMessage(OllamaResponseError, "HTTP 404") as context:
            self.client.chat([{"role": "user", "content": "Test"}])

        self.assertNotIn("tajna odpowiedz", str(context.exception))

    @patch("backend.ollama.urlopen")
    def test_rejects_invalid_json_response(self, mocked_urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b"not-json"
        mocked_urlopen.return_value = response

        with self.assertRaisesMessage(OllamaResponseError, "invalid JSON"):
            self.client.list_models()

    @patch("backend.ollama.urlopen")
    def test_rejects_chat_response_without_content(self, mocked_urlopen):
        mocked_urlopen.return_value = self.response(
            {"model": "llama3.1:8b", "message": {"role": "assistant"}}
        )

        with self.assertRaisesMessage(OllamaResponseError, "no content"):
            self.client.chat([{"role": "user", "content": "Test"}])
