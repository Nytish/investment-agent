"""
model_router.py — LLM provider fallback chain for APEX agent layer.

Priority order (local-first for privacy):
  1. Ollama qwen2.5:14b-instruct-q4_K_M  (Mac Mini M4, 16GB unified memory — primary)
  2. Ollama qwen2.5:3b                   (fast local fallback, ~2GB)
  3. Gemini 2.5 Flash                    (cloud fallback)
  4. Gemini 1.5 Flash                    (secondary cloud)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import requests


@runtime_checkable
class LLMProvider(Protocol):
    def available(self) -> bool: ...
    def complete(self, messages: list[dict]) -> str: ...
    @property
    def name(self) -> str: ...


@dataclass
class OllamaProvider:
    model: str = "qwen2.5:14b-instruct-q4_K_M"
    base_url: str = "http://localhost:11434"

    @property
    def name(self) -> str:
        return f"Ollama({self.model})"

    def available(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=2)
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            return any(self.model in m for m in models)
        except Exception:
            return False

    def complete(self, messages: list[dict]) -> str:
        r = requests.post(
            f"{self.base_url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False},
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["message"]["content"]


@dataclass
class GeminiProvider:
    model: str = "gemini-2.5-flash"
    _api_base: str = field(
        default="https://generativelanguage.googleapis.com/v1beta/models",
        repr=False,
    )

    @property
    def name(self) -> str:
        return f"Gemini({self.model})"

    def available(self) -> bool:
        return bool(os.getenv("GEMINI_API_KEY"))

    def complete(self, messages: list[dict]) -> str:
        api_key = os.environ["GEMINI_API_KEY"]
        url = f"{self._api_base}/{self.model}:generateContent?key={api_key}"

        # Convert OpenAI-style messages → Gemini format
        # System message gets folded into first user turn
        contents: list[dict] = []
        system_text: str = ""

        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                system_text = content
            elif role == "user":
                text = f"{system_text}\n\n{content}".strip() if system_text else content
                contents.append({"role": "user", "parts": [{"text": text}]})
                system_text = ""  # consumed
            elif role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content}]})

        r = requests.post(url, json={"contents": contents}, timeout=60)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]


class ModelRouter:
    """Try providers in priority order. First available and responsive wins."""

    DEFAULT_PROVIDERS: list[LLMProvider] = [
        OllamaProvider("qwen2.5:14b-instruct-q4_K_M"),  # Mac Mini M4 16GB — primary, private
        OllamaProvider("qwen2.5:3b"),                    # fast local fallback, ~2GB
        GeminiProvider("gemini-2.5-flash"),              # cloud fallback
        GeminiProvider("gemini-1.5-flash"),              # secondary cloud
    ]

    def __init__(self, providers: list[LLMProvider] | None = None) -> None:
        self.providers = providers if providers is not None else list(self.DEFAULT_PROVIDERS)

    def route(self, messages: list[dict]) -> tuple[str, str]:
        """
        Returns (response_text, provider_name).
        Raises RuntimeError if no provider is available.
        """
        last_error: Exception | None = None
        for provider in self.providers:
            if not provider.available():
                continue
            try:
                response = provider.complete(messages)
                return response, provider.name
            except Exception as exc:
                last_error = exc
                continue

        detail = f": {last_error}" if last_error else ""
        raise RuntimeError(
            f"No LLM provider available{detail}. "
            "Start Ollama (`ollama run qwen2.5:14b-instruct-q4_K_M`) or set GEMINI_API_KEY."
        )
