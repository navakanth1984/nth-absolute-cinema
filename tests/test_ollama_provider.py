from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.model_manager.ollama_provider import OllamaProvider, OllamaNotReachableError


def test_generate_returns_response_text():
    provider = OllamaProvider(model="gemma2:9b")
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "response": "Once upon a time...",
        "eval_count": 42,
        "prompt_eval_count": 8,
    }
    fake_response.raise_for_status.return_value = None
    with patch("requests.post", return_value=fake_response) as mock_post:
        result = provider.generate("Write a story opening.")
    assert result == "Once upon a time..."
    mock_post.assert_called_once()
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["json"]["model"] == "gemma2:9b"
    assert call_kwargs["json"]["prompt"] == "Write a story opening."
    assert call_kwargs["json"]["stream"] is False
    assert provider.last_call_tokens == 50


def test_generate_raises_actionable_error_when_unreachable():
    provider = OllamaProvider(model="gemma2:9b")
    import requests

    with patch("requests.post", side_effect=requests.ConnectionError("refused")):
        try:
            provider.generate("hello")
            assert False, "expected OllamaNotReachableError"
        except OllamaNotReachableError as e:
            assert "ollama.com" in str(e)
            assert "gemma2:9b" in str(e)
