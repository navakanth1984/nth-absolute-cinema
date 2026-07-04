"""GeminiProvider - cloud LlmProvider backed by Google's Generative Language API.
Reads GEMINI_API_KEY from the environment; raises loudly (not silently) if the key
is missing when this provider is explicitly constructed - same contract as
OpenRouterProvider."""
from __future__ import annotations

import os
import time

import requests


class GeminiNotConfiguredError(RuntimeError):
    pass


class GeminiBlockedResponseError(RuntimeError):
    """Raised when Gemini returns no candidates (safety filters, recitation
    block, etc.) instead of an HTTP error - this must surface as a real error,
    not a silent empty string or an opaque IndexError."""


class GeminiProvider:
    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        timeout_s: float = 60.0,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.timeout_s = timeout_s
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        if not self._api_key:
            raise GeminiNotConfiguredError(
                "GEMINI_API_KEY not set in environment - required to construct "
                "GeminiProvider."
            )
        self.last_call_duration_s: float = 0.0
        self.last_call_tokens: int = 0

    def generate(self, prompt: str, system: str = "") -> str:
        body: dict = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        start = time.monotonic()
        resp = requests.post(
            f"{self.base_url}/models/{self.model}:generateContent",
            params={"key": self._api_key},
            json=body,
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        self.last_call_duration_s = time.monotonic() - start
        data = resp.json()
        usage = data.get("usageMetadata", {})
        self.last_call_tokens = int(usage.get("totalTokenCount", 0))
        candidates = data.get("candidates") or []
        if not candidates:
            reason = data.get("promptFeedback", {}).get("blockReason", "unknown")
            raise GeminiBlockedResponseError(
                f"Gemini returned no candidates (blockReason={reason}) - the prompt "
                "was likely filtered rather than a transport failure."
            )
        return candidates[0]["content"]["parts"][0]["text"]
