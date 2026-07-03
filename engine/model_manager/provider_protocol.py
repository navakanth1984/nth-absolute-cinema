"""LlmProvider protocol - every compiler talks to this interface only, never to a
concrete provider class. ModelManager.resolve() picks which implementation backs it;
compilers never know or care which one they got."""
from __future__ import annotations

from typing import Protocol


class LlmProvider(Protocol):
    model: str
    last_call_duration_s: float
    last_call_tokens: int

    def generate(self, prompt: str, system: str = "") -> str:
        ...
