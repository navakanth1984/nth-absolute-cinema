from pathlib import Path
import sys
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.model_manager.orchestrator import LlmOrchestrator


def test_generate_returns_text_and_metrics():
    fake_provider = MagicMock()
    fake_provider.model = "gemma2:9b"
    fake_provider.last_call_tokens = 120
    fake_provider.generate.return_value = "Once upon a time..."

    orchestrator = LlmOrchestrator(fake_provider)
    text, metrics = orchestrator.generate("Write a story opening.")

    assert text == "Once upon a time..."
    assert metrics["model"] == "gemma2:9b"
    assert metrics["tokens"] == 120
    assert metrics["attempts"] == 1
    assert "duration_s" in metrics


def test_retries_on_transient_failure_then_succeeds():
    fake_provider = MagicMock()
    fake_provider.model = "gemma2:9b"
    fake_provider.last_call_tokens = 50
    fake_provider.generate.side_effect = [
        RuntimeError("transient network blip"),
        "Recovered output",
    ]

    orchestrator = LlmOrchestrator(fake_provider)
    text, metrics = orchestrator.generate("prompt")

    assert text == "Recovered output"
    assert metrics["attempts"] == 2
    assert fake_provider.generate.call_count == 2


def test_raises_after_exhausting_retries():
    fake_provider = MagicMock()
    fake_provider.model = "gemma2:9b"
    fake_provider.generate.side_effect = RuntimeError("permanent failure")

    orchestrator = LlmOrchestrator(fake_provider)
    try:
        orchestrator.generate("prompt")
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "permanent failure" in str(e)
    assert fake_provider.generate.call_count == 3  # 1 + TRANSIENT_RETRY_COUNT
