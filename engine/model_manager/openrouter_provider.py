"""OpenRouterProvider - cloud fallback LlmProvider for development when Ollama isn't
running locally. Reads OPENROUTER_API_KEY from the environment; raises loudly (not
silently) if the key is missing when this provider is explicitly constructed."""
from __future__ import annotations

import os
import time

import requests


class OpenRouterNotConfiguredError(RuntimeError):
    pass


class OpenRouterProvider:
    def __init__(
        self,
        model: str = "google/gemma-4-31b-it:free",
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_s: float = 90.0,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.timeout_s = timeout_s
        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not self._api_key:
            raise OpenRouterNotConfiguredError(
                "OPENROUTER_API_KEY not set in environment - required to construct "
                "OpenRouterProvider."
            )
        self.last_call_duration_s: float = 0.0
        self.last_call_tokens: int = 0

    def generate(self, prompt: str, system: str = "") -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        start = time.monotonic()
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={"model": self.model, "messages": messages},
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        self.last_call_duration_s = time.monotonic() - start
        data = resp.json()
        usage = data.get("usage", {})
        self.last_call_tokens = int(usage.get("total_tokens", 0))
        return data["choices"][0]["message"]["content"]
