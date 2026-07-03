from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.model_manager.fallback_provider import FallbackProvider
from engine.model_manager.mock_provider import MockProvider


class _FailingProvider:
    model = "failing-provider"
    last_call_duration_s = 0.0
    last_call_tokens = 0

    def __init__(self, error: Exception) -> None:
        self._error = error

    def generate(self, prompt: str, system: str = "") -> str:
        raise self._error


def test_uses_first_provider_when_it_succeeds():
    mock = MockProvider()
    chain = FallbackProvider([mock])
    output = chain.generate("hello")
    assert "MOCK OUTPUT" in output
    assert chain.active_provider_name == "MockProvider"


def test_falls_through_to_second_provider_on_failure():
    events = []
    failing = _FailingProvider(RuntimeError("429 rate limited"))
    mock = MockProvider()
    chain = FallbackProvider([failing, mock], on_fallback=lambda p, e: events.append((type(p).__name__, str(e))))

    output = chain.generate("hello")

    assert "MOCK OUTPUT" in output
    assert chain.active_provider_name == "MockProvider"
    assert events == [("_FailingProvider", "429 rate limited")]


def test_raises_last_error_when_every_provider_fails():
    chain = FallbackProvider([_FailingProvider(ValueError("first")), _FailingProvider(ValueError("second"))])
    try:
        chain.generate("hello")
        assert False, "expected ValueError"
    except ValueError as e:
        assert str(e) == "second"


def test_requires_at_least_one_provider():
    try:
        FallbackProvider([])
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_provider_chain_names():
    chain = FallbackProvider([MockProvider(), MockProvider()])
    assert chain.provider_chain_names == ["MockProvider", "MockProvider"]
