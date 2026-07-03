"""resolve_provider() - ModelManager's provider selection, Sprint 1 scope.

Chain: Ollama (if reachable) -> OpenRouter (if OPENROUTER_API_KEY set) -> MockProvider.
Compilers never call a concrete provider class directly - only this function, so
swapping/adding providers (LM Studio, llama.cpp, Gemini) later never touches compiler
code. Full COMPUTE_MANAGER_SPEC.md-driven resolution (hardware profile aware) is
Sprint 2+; this is the Sprint 1 dev-friendly subset of that same idea.
"""
from __future__ import annotations

import os

import requests

from engine.model_manager.mock_provider import MockProvider
from engine.model_manager.ollama_provider import OllamaProvider
from engine.model_manager.openrouter_provider import (
    OpenRouterNotConfiguredError,
    OpenRouterProvider,
)
from engine.model_manager.provider_protocol import LlmProvider


def _ollama_reachable(base_url: str, timeout_s: float = 1.5) -> bool:
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=timeout_s)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def resolve_provider(
    ollama_model: str = "gemma2:9b",
    openrouter_model: str = "google/gemma-4-31b-it:free",
    base_url: str = "http://localhost:11434",
    force: str | None = None,
) -> LlmProvider:
    """force: "ollama" | "openrouter" | "mock" to bypass auto-detection (tests use
    this); None runs the real fallback chain."""
    if force == "ollama":
        return OllamaProvider(model=ollama_model, base_url=base_url)
    if force == "openrouter":
        return OpenRouterProvider(model=openrouter_model)
    if force == "mock":
        return MockProvider()

    if _ollama_reachable(base_url):
        return OllamaProvider(model=ollama_model, base_url=base_url)

    if os.environ.get("OPENROUTER_API_KEY"):
        try:
            return OpenRouterProvider(model=openrouter_model)
        except OpenRouterNotConfiguredError:
            pass

    return MockProvider()
