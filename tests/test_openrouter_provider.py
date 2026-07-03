from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.model_manager.openrouter_provider import (
    OpenRouterProvider,
    OpenRouterNotConfiguredError,
)


def test_raises_when_no_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    try:
        OpenRouterProvider(api_key=None)
        assert False, "expected OpenRouterNotConfiguredError"
    except OpenRouterNotConfiguredError:
        pass


def test_generate_returns_message_content(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    provider = OpenRouterProvider()

    fake_response = MagicMock()
    fake_response.json.return_value = {
        "choices": [{"message": {"content": "Once upon a time..."}}],
        "usage": {"total_tokens": 55},
    }
    fake_response.raise_for_status.return_value = None
    with patch("requests.post", return_value=fake_response) as mock_post:
        result = provider.generate("Write a story opening.")

    assert result == "Once upon a time..."
    assert provider.last_call_tokens == 55
    headers = mock_post.call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer fake-key"
