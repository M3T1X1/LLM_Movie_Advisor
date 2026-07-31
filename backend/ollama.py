import json
import math
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


@dataclass(frozen=True)
class OllamaEmbeddingResponse:
    embeddings: tuple[tuple[float, ...], ...]
    model: str
    total_duration_ns: int | None
    load_duration_ns: int | None
    prompt_eval_count: int | None


class OllamaClient:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        request_timeout: float,
        health_timeout: float,
        embedding_model: str = "",
        embedding_dimensions: int = 768,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model.strip()
        self.request_timeout = request_timeout
        self.health_timeout = health_timeout
        self.embedding_model = embedding_model.strip()
        self.embedding_dimensions = embedding_dimensions
        if not self.base_url:
            raise OllamaConfigurationError("Ollama base URL cannot be empty.")
        if not self.model:
            raise OllamaConfigurationError("Ollama model cannot be empty.")
        if self.request_timeout <= 0 or self.health_timeout <= 0:
            raise OllamaConfigurationError(
                "Ollama timeouts must be greater than zero."
            )
        if self.embedding_dimensions <= 0:
            raise OllamaConfigurationError(
                "Ollama embedding dimensions must be greater than zero."
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
        return self.is_model_available(self.model, self.list_models())

    def has_configured_embedding_model(self) -> bool:
        if not self.embedding_model:
            return False
        return self.is_model_available(self.embedding_model, self.list_models())

    def missing_configured_models(self) -> tuple[str, ...]:
        available_models = self.list_models()
        configured_models = (self.model, self.embedding_model)
        return tuple(
            model
            for model in configured_models
            if model and not self.is_model_available(model, available_models)
        )

    @staticmethod
    def is_model_available(model: str, available_models: tuple[str, ...]) -> bool:
        expected_names = {model}
        if ":" not in model:
            expected_names.add(f"{model}:latest")
        return bool(expected_names.intersection(available_models))

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

    def embed(self, texts: list[str]) -> OllamaEmbeddingResponse:
        if not self.embedding_model:
            raise OllamaConfigurationError(
                "Ollama embedding model cannot be empty."
            )
        normalized_texts = self._validate_embedding_texts(texts)
        payload = self._request(
            "POST",
            "/api/embed",
            payload={
                "model": self.embedding_model,
                "input": normalized_texts,
                "truncate": True,
            },
            timeout=self.request_timeout,
        )
        raw_embeddings = payload.get("embeddings")
        if not isinstance(raw_embeddings, list) or len(raw_embeddings) != len(
            normalized_texts
        ):
            raise OllamaResponseError(
                "Ollama returned an invalid embedding batch."
            )

        embeddings: list[tuple[float, ...]] = []
        for raw_embedding in raw_embeddings:
            if not isinstance(raw_embedding, list) or len(
                raw_embedding
            ) != self.embedding_dimensions:
                raise OllamaResponseError(
                    "Ollama returned an embedding with invalid dimensions."
                )
            embedding: list[float] = []
            for value in raw_embedding:
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise OllamaResponseError(
                        "Ollama returned a non-numeric embedding."
                    )
                normalized_value = float(value)
                if not math.isfinite(normalized_value):
                    raise OllamaResponseError(
                        "Ollama returned a non-finite embedding."
                    )
                embedding.append(normalized_value)
            embeddings.append(tuple(embedding))

        response_model = payload.get("model")
        if not isinstance(response_model, str) or not response_model.strip():
            response_model = self.embedding_model
        return OllamaEmbeddingResponse(
            embeddings=tuple(embeddings),
            model=response_model,
            total_duration_ns=self._optional_int(payload.get("total_duration")),
            load_duration_ns=self._optional_int(payload.get("load_duration")),
            prompt_eval_count=self._optional_int(payload.get("prompt_eval_count")),
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
    def _validate_embedding_texts(texts: list[str]) -> list[str]:
        if not isinstance(texts, list) or not texts:
            raise ValueError("At least one embedding text is required.")
        normalized: list[str] = []
        for text in texts:
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Embedding text cannot be empty.")
            normalized.append(text.strip())
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
        embedding_model=settings.OLLAMA_EMBEDDING_MODEL,
        embedding_dimensions=settings.OLLAMA_EMBEDDING_DIMENSIONS,
        request_timeout=settings.OLLAMA_REQUEST_TIMEOUT_SECONDS,
        health_timeout=settings.OLLAMA_HEALTH_TIMEOUT_SECONDS,
    )
