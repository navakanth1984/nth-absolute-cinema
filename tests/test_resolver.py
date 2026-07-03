from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.model_manager.resolver import resolve_provider
from engine.model_manager.ollama_provider import OllamaProvider
from engine.model_manager.openrouter_provider import OpenRouterProvider
from engine.model_manager.mock_provider import MockProvider


def test_falls_back_to_ollama_when_reachable():
    with patch("engine.model_manager.resolver._ollama_reachable", return_value=True):
        provider = resolve_provider()
    assert isinstance(provider, OllamaProvider)


def test_falls_back_to_openrouter_when_ollama_unreachable(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    with patch("engine.model_manager.resolver._ollama_reachable", return_value=False):
        provider = resolve_provider()
    assert isinstance(provider, OpenRouterProvider)


def test_falls_back_to_mock_when_nothing_available(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with patch("engine.model_manager.resolver._ollama_reachable", return_value=False):
        provider = resolve_provider()
    assert isinstance(provider, MockProvider)


def test_force_bypasses_autodetection():
    provider = resolve_provider(force="mock")
    assert isinstance(provider, MockProvider)
