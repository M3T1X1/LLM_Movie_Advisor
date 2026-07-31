import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


class OllamaError(Exception):
    """Base error raised for controlled Ollama failures."""


class OllamaConfigurationError(OllamaError):
    """Raised when the configured Ollama connection values are invalid."""


class OllamaUnavailableError(OllamaError):
    """Raised when the Ollama HTTP service cannot be reached."""


class OllamaResponseError(OllamaError):
    """Raised when Ollama returns an unsuccessful or invalid response."""


@dataclass(frozen=True)
class OllamaChatResponse:
    content: str
    model: str
    done_reason: str | None
    total_duration_ns: int | None
    prompt_eval_count: int | None
    eval_count: int | None


class OllamaClient:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        request_timeout: float,
        health_timeout: float,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model.strip()
        self.request_timeout = request_timeout
        self.health_timeout = health_timeout
        if not self.base_url:
            raise OllamaConfigurationError("Ollama base URL cannot be empty.")
        if not self.model:
            raise OllamaConfigurationError("Ollama model cannot be empty.")
        if self.request_timeout <= 0 or self.health_timeout <= 0:
            raise OllamaConfigurationError(
                "Ollama timeouts must be greater than zero."
            )

    def list_models(self) -> tuple[str, ...]:
        payload = self._request("GET", "/api/tags", timeout=self.health_timeout)
        raw_models = payload.get("models")
        if not isinstance(raw_models, list):
            raise OllamaResponseError("Ollama returned an invalid model list.")

        names: list[str] = []
        for item in raw_models:
            if not isinstance(item, dict):
                continue
            name = item.get("model") or item.get("name")
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
        return tuple(dict.fromkeys(names))

    def has_configured_model(self) -> bool:
        expected_names = {self.model}
        if ":" not in self.model:
            expected_names.add(f"{self.model}:latest")
        return bool(expected_names.intersection(self.list_models()))

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        response_format: str | dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> OllamaChatResponse:
        normalized_messages = self._validate_messages(messages)
        request_payload: dict[str, Any] = {
            "model": self.model,
            "messages": normalized_messages,
            "stream": False,
        }
        if response_format is not None:
            request_payload["format"] = response_format
        if options is not None:
            request_payload["options"] = options

        payload = self._request(
            "POST",
            "/api/chat",
            payload=request_payload,
            timeout=self.request_timeout,
        )
        message = payload.get("message")
        if not isinstance(message, dict):
            raise OllamaResponseError("Ollama chat response has no message.")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise OllamaResponseError("Ollama chat response has no content.")

        response_model = payload.get("model")
        if not isinstance(response_model, str) or not response_model.strip():
            response_model = self.model
        done_reason = payload.get("done_reason")
        if not isinstance(done_reason, str):
            done_reason = None

        return OllamaChatResponse(
            content=content.strip(),
            model=response_model,
            done_reason=done_reason,
            total_duration_ns=self._optional_int(payload.get("total_duration")),
            prompt_eval_count=self._optional_int(payload.get("prompt_eval_count")),
            eval_count=self._optional_int(payload.get("eval_count")),
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        timeout: float,
    ) -> dict[str, Any]:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                raw_payload = response.read()
        except HTTPError as error:
            raise OllamaResponseError(
                f"Ollama request failed with HTTP {error.code}."
            ) from error
        except (URLError, TimeoutError, OSError) as error:
            raise OllamaUnavailableError(
                "Ollama service is unavailable."
            ) from error

        try:
            decoded = json.loads(raw_payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise OllamaResponseError("Ollama returned invalid JSON.") from error
        if not isinstance(decoded, dict):
            raise OllamaResponseError("Ollama returned an invalid response.")
        return decoded

    @staticmethod
    def _validate_messages(
        messages: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        if not isinstance(messages, list) or not messages:
            raise ValueError("At least one Ollama chat message is required.")

        normalized: list[dict[str, str]] = []
        allowed_roles = {"system", "user", "assistant"}
        for message in messages:
            if not isinstance(message, dict):
                raise ValueError("Ollama chat messages must be objects.")
            role = message.get("role")
            content = message.get("content")
            if role not in allowed_roles:
                raise ValueError("Unsupported Ollama chat message role.")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Ollama chat message content cannot be empty.")
            normalized.append({"role": role, "content": content.strip()})
        return normalized

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        return value


def get_ollama_client() -> OllamaClient:
    return OllamaClient(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_CHAT_MODEL,
        request_timeout=settings.OLLAMA_REQUEST_TIMEOUT_SECONDS,
        health_timeout=settings.OLLAMA_HEALTH_TIMEOUT_SECONDS,
    )
