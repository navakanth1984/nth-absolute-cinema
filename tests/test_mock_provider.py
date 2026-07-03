from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.model_manager.mock_provider import MockProvider


def test_generate_returns_deterministic_labeled_output():
    provider = MockProvider()
    result = provider.generate("Write a story about a temple.", system="You are a writer.")
    assert "MOCK OUTPUT" in result
    assert provider.last_call_tokens > 0

    result2 = provider.generate("Write a story about a temple.", system="You are a writer.")
    assert result == result2  # deterministic for same input
