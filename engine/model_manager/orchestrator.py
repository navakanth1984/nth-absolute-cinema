"""LlmOrchestrator - thin layer between compilers and LlmProvider (provider_protocol.py).
Compilers never call a provider directly; they call orchestrator.generate(), which
adds retry-on-transient-failure and always returns a metrics dict alongside the text.
Structured-output enforcement, prompt versioning, and multi-pass refinement are
noted here as explicit future extension points on this same class - not built yet,
not silently assumed either."""
from __future__ import annotations

import time

from engine.model_manager.provider_protocol import LlmProvider

TRANSIENT_RETRY_COUNT = 2


class LlmOrchestrator:
    def __init__(self, provider: LlmProvider) -> None:
        self._provider = provider

    @property
    def provider_name(self) -> str:
        return type(self._provider).__name__

    @property
    def model(self) -> str:
        return self._provider.model

    def generate(self, prompt: str, system: str = "") -> tuple[str, dict]:
        last_error: Exception | None = None
        start = time.monotonic()
        for attempt in range(1 + TRANSIENT_RETRY_COUNT):
            try:
                output = self._provider.generate(prompt, system=system)
                total_duration_s = time.monotonic() - start
                metrics = {
                    "provider": self.provider_name,
                    "model": self._provider.model,
                    "duration_s": round(total_duration_s, 3),
                    "tokens": self._provider.last_call_tokens,
                    "attempts": attempt + 1,
                    "cost_usd": 0.0,
                }
                return output, metrics
            except Exception as e:  # noqa: BLE001 - deliberately broad: any provider failure is retryable here
                last_error = e
                if attempt < TRANSIENT_RETRY_COUNT:
                    continue
        assert last_error is not None
        raise last_error
