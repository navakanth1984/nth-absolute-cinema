"""MockProvider - deterministic, offline, zero-dependency LlmProvider for unit tests
and for development when neither Ollama nor OpenRouter is available. Satisfies
LlmProvider protocol exactly like OllamaProvider/OpenRouterProvider do."""
from __future__ import annotations

import hashlib
import time


class MockProvider:
    model = "mock-provider"

    def __init__(self) -> None:
        self.last_call_duration_s: float = 0.0
        self.last_call_tokens: int = 0

    def generate(self, prompt: str, system: str = "") -> str:
        start = time.monotonic()
        seed = hashlib.sha256((system + prompt).encode("utf-8")).hexdigest()[:8]
        output = (
            f"[MOCK OUTPUT seed={seed}] Generated response for prompt of "
            f"{len(prompt)} chars under system context of {len(system)} chars. "
            f"This is deterministic placeholder content for offline development - "
            f"not a real generation."
        )
        self.last_call_duration_s = time.monotonic() - start
        self.last_call_tokens = len(prompt.split()) + len(output.split())
        return output
