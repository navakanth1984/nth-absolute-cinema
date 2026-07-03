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
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from engine.model_manager.provider_protocol import LlmProvider


class ProviderTimeoutError(RuntimeError):
    """Raised when a provider exceeds its hard wall-clock deadline.

    requests' own `timeout=` only caps inactivity between socket reads, not
    total call duration - a response that trickles data slowly (or a proxy that
    keeps the connection alive with periodic bytes) never trips it even if the
    whole call runs for minutes. Observed live during Sprint 2A.2 UAT: a
    screenplay generation call configured with timeout_s=15 ran well past that
    with no error. This class backs a real, enforced wall-clock cap around each
    provider call in the fallback chain."""


class FallbackProvider:
    """Tries providers in order; on the first one that succeeds, remembers which
    provider actually served the request (for metrics/diagnostics) and returns
    its output. Raises the last error only if every provider in the chain fails.

    Each provider call is wrapped in a hard wall-clock deadline (its own
    `timeout_s` attribute if it has one, else no deadline) enforced via a worker
    thread - not just the provider's own internal `requests` timeout, which does
    not reliably cap total duration (see ProviderTimeoutError)."""

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

    def _call_with_deadline(self, provider: LlmProvider, prompt: str, system: str) -> str:
        """Note: if the deadline fires, the worker thread running provider.generate()
        keeps running in the background until it eventually completes or errors on
        its own - Python cannot forcibly kill a thread. What this buys is the thing
        that actually matters for the UI: FallbackProvider.generate() returns (and
        falls through to the next provider) as soon as the deadline elapses,
        instead of the caller blocking on a call that may never return."""
        deadline = getattr(provider, "timeout_s", None)
        if deadline is None:
            return provider.generate(prompt, system=system)
        # Deliberately not a `with` block: ThreadPoolExecutor.__exit__ calls
        # shutdown(wait=True), which blocks until the worker thread finishes -
        # exactly the hang this method exists to avoid. shutdown(wait=False)
        # lets the caller return immediately; the orphaned thread is cleaned up
        # by the interpreter when it eventually finishes or the process exits.
        pool = ThreadPoolExecutor(max_workers=1)
        future = pool.submit(provider.generate, prompt, system=system)
        try:
            return future.result(timeout=deadline)
        except FutureTimeoutError:
            raise ProviderTimeoutError(
                f"{type(provider).__name__} exceeded its {deadline}s wall-clock deadline"
            ) from None
        finally:
            pool.shutdown(wait=False)

    def generate(self, prompt: str, system: str = "") -> str:
        last_error: Exception | None = None
        for provider in self._providers:
            try:
                output = self._call_with_deadline(provider, prompt, system)
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
