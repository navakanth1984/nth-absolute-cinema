from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.model_manager.fallback_provider import FallbackProvider, ProviderTimeoutError
from engine.model_manager.mock_provider import MockProvider


class _FailingProvider:
    model = "failing-provider"
    last_call_duration_s = 0.0
    last_call_tokens = 0

    def __init__(self, error: Exception) -> None:
        self._error = error

    def generate(self, prompt: str, system: str = "") -> str:
        raise self._error


class _SlowProvider:
    """Simulates a provider whose own internal timeout never fires because it
    keeps trickling activity (the exact real-world bug this hard deadline
    exists to catch) - sleeps far longer than its declared timeout_s."""

    model = "slow-provider"
    timeout_s = 0.2
    last_call_duration_s = 0.0
    last_call_tokens = 0

    def generate(self, prompt: str, system: str = "") -> str:
        time.sleep(5.0)
        return "should never get here within the test"


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


def test_hard_deadline_falls_through_when_provider_hangs_past_its_own_timeout():
    """The real bug found live during Sprint 2A.2 UAT: a provider's own internal
    requests timeout doesn't cap total duration for a slowly-trickling response.
    This asserts FallbackProvider enforces a hard wall-clock deadline regardless
    of what the provider's own timeout logic does."""
    events = []
    chain = FallbackProvider(
        [_SlowProvider(), MockProvider()],
        on_fallback=lambda p, e: events.append((type(p).__name__, type(e).__name__)),
    )

    start = time.monotonic()
    output = chain.generate("hello")
    elapsed = time.monotonic() - start

    assert "MOCK OUTPUT" in output
    assert elapsed < 2.0  # well under the SlowProvider's 5s sleep - deadline (0.2s) was enforced
    assert events == [("_SlowProvider", "ProviderTimeoutError")]


def test_provider_without_timeout_s_gets_no_hard_deadline():
    """MockProvider has no timeout_s attribute - it should run as a normal
    blocking call, not be wrapped in a deadline it never declared."""
    chain = FallbackProvider([MockProvider()])
    output = chain.generate("hello")
    assert "MOCK OUTPUT" in output
