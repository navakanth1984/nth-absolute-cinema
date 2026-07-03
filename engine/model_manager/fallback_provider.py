"""FallbackProvider - Sprint 2A.1: a provider should never make the whole
pipeline unusable just because one upstream (e.g. OpenRouter's free tier) is
rate-limited or unreachable. Wraps an ordered list of LlmProvider instances and
tries each in turn at generate()-time, not just once at Studio construction -
so a mid-session OpenRouter 429 falls through to MockProvider instead of
failing the request outright.

This is intentionally a thin fallback chain, not a scheduler: no backoff,
no cost-aware routing, no health caching across calls. Those are real future
work (COMPUTE_MANAGER_SPEC.md's hardware-aware resolution), not something to
half-build here.
"""
from __future__ import annotations

from collections.abc import Callable

from engine.model_manager.provider_protocol import LlmProvider


class FallbackProvider:
    """Tries providers in order; on the first one that succeeds, remembers which
    provider actually served the request (for metrics/diagnostics) and returns
    its output. Raises the last error only if every provider in the chain fails."""

    def __init__(
        self,
        providers: list[LlmProvider],
        on_fallback: Callable[[LlmProvider, Exception], None] | None = None,
    ) -> None:
        if not providers:
            raise ValueError("FallbackProvider requires at least one provider")
        self._providers = providers
        self._on_fallback = on_fallback
        self._active: LlmProvider = providers[0]
        self.last_call_duration_s: float = 0.0
        self.last_call_tokens: int = 0

    @property
    def model(self) -> str:
        return self._active.model

    @property
    def active_provider_name(self) -> str:
        return type(self._active).__name__

    @property
    def provider_chain_names(self) -> list[str]:
        return [type(p).__name__ for p in self._providers]

    def generate(self, prompt: str, system: str = "") -> str:
        last_error: Exception | None = None
        for provider in self._providers:
            try:
                output = provider.generate(prompt, system=system)
            except Exception as e:  # noqa: BLE001 - any provider failure falls through to the next
                last_error = e
                if self._on_fallback is not None:
                    self._on_fallback(provider, e)
                continue
            self._active = provider
            self.last_call_duration_s = getattr(provider, "last_call_duration_s", 0.0)
            self.last_call_tokens = getattr(provider, "last_call_tokens", 0)
            return output
        assert last_error is not None
        raise last_error
