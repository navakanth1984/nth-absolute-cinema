from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.model_manager.gemini_provider import (
    GeminiProvider,
    GeminiNotConfiguredError,
    GeminiBlockedResponseError,
)


def test_raises_when_no_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    try:
        GeminiProvider(api_key=None)
        assert False, "expected GeminiNotConfiguredError"
    except GeminiNotConfiguredError:
        pass


def test_generate_returns_candidate_text(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    provider = GeminiProvider()

    fake_response = MagicMock()
    fake_response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Once upon a time..."}]}}],
        "usageMetadata": {"totalTokenCount": 42},
    }
    fake_response.raise_for_status.return_value = None
    with patch("requests.post", return_value=fake_response) as mock_post:
        result = provider.generate("Write a story opening.")

    assert result == "Once upon a time..."
    assert provider.last_call_tokens == 42
    assert mock_post.call_args.kwargs["params"] == {"key": "fake-key"}


def test_generate_sends_system_instruction(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    provider = GeminiProvider()

    fake_response = MagicMock()
    fake_response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "ok"}]}}],
    }
    fake_response.raise_for_status.return_value = None
    with patch("requests.post", return_value=fake_response) as mock_post:
        provider.generate("prompt", system="You are a helpful assistant.")

    body = mock_post.call_args.kwargs["json"]
    assert body["systemInstruction"] == {"parts": [{"text": "You are a helpful assistant."}]}


def test_generate_raises_on_empty_candidates(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    provider = GeminiProvider()

    fake_response = MagicMock()
    fake_response.json.return_value = {
        "candidates": [],
        "promptFeedback": {"blockReason": "SAFETY"},
    }
    fake_response.raise_for_status.return_value = None
    with patch("requests.post", return_value=fake_response):
        try:
            provider.generate("prompt")
            assert False, "expected GeminiBlockedResponseError"
        except GeminiBlockedResponseError as e:
            assert "SAFETY" in str(e)
