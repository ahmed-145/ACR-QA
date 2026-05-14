"""Ollama LLM provider — OpenAI-compatible client for local inference.

Wraps the Ollama API (http://localhost:11434/v1) in the same interface as
the Groq client so KeyPool can dispatch to it transparently.
Model defaults:
  ACRQA_LLM_MODEL       — main model (default: qwen2.5-coder:1.5b)
  ACRQA_LLM_MODEL_FAST  — fast model for path feasibility (default: same)
  OLLAMA_BASE_URL       — override base URL (default: http://localhost:11434)
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:11434"
_DEFAULT_MODEL = "qwen2.5-coder:1.5b"


def _ollama_base() -> str:
    return os.getenv("OLLAMA_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")


def ollama_model() -> str:
    return os.getenv("ACRQA_LLM_MODEL", _DEFAULT_MODEL)


def ollama_model_fast() -> str:
    return os.getenv("ACRQA_LLM_MODEL_FAST", ollama_model())


def ollama_chat_url() -> str:
    return f"{_ollama_base()}/v1/chat/completions"


class _OllamaChoice:
    """Mimics groq.types.chat.ChatCompletionMessage structure."""

    class _Message:
        def __init__(self, content: str) -> None:
            self.content = content

    def __init__(self, content: str) -> None:
        self.message = self._Message(content)


class _OllamaUsage:
    def __init__(self, total_tokens: int) -> None:
        self.total_tokens = total_tokens


class _OllamaCompletion:
    """Mimics groq ChatCompletion for drop-in use in ExplanationEngine."""

    def __init__(self, content: str, total_tokens: int = 0) -> None:
        self.choices = [_OllamaChoice(content)]
        self.usage = _OllamaUsage(total_tokens)


class OllamaClient:
    """Synchronous Ollama client — same .chat.completions.create() interface as Groq."""

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self._base_url = (base_url or _ollama_base()).rstrip("/")
        self._model = model or ollama_model()
        self.chat = _OllamaChatNamespace(self._base_url, self._model)

    @property
    def model(self) -> str:
        return self._model

    def is_available(self) -> bool:
        """Return True if the Ollama server is reachable."""
        try:
            with httpx.Client(timeout=3.0) as client:
                r = client.get(f"{self._base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False


class _OllamaChatNamespace:
    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url
        self._model = model
        self.completions = _OllamaCompletionsNamespace(base_url, model)


class _OllamaCompletionsNamespace:
    def __init__(self, base_url: str, model: str) -> None:
        self._url = f"{base_url}/v1/chat/completions"
        self._model = model

    def create(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int = 300,
        temperature: float = 0.3,
        **_: Any,
    ) -> _OllamaCompletion:
        payload = {
            "model": model or self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(self._url, json=payload)
            resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        total_tokens = data.get("usage", {}).get("total_tokens", 0)
        return _OllamaCompletion(content, total_tokens)
