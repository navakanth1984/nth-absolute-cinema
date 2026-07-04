from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.model_manager.tts_fallback_provider import TtsFallbackProvider


class _FailingBackend:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def synthesize(self, text: str, out_path: Path) -> Path:
        raise self._error


class _StubBackend:
    def synthesize(self, text: str, out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(f"audio-for:{text}")
        return out_path


def test_uses_first_backend_when_it_succeeds(tmp_path):
    chain = TtsFallbackProvider([_StubBackend()])
    out = chain.synthesize("hello", tmp_path / "out.wav")
    assert out.read_text() == "audio-for:hello"
    assert chain.active_backend_name == "_StubBackend"


def test_falls_through_to_second_backend_on_failure(tmp_path):
    events = []
    failing = _FailingBackend(RuntimeError("quota exceeded"))
    stub = _StubBackend()
    chain = TtsFallbackProvider(
        [failing, stub], on_fallback=lambda b, e: events.append((type(b).__name__, str(e)))
    )

    out = chain.synthesize("hello", tmp_path / "out.wav")

    assert out.read_text() == "audio-for:hello"
    assert chain.active_backend_name == "_StubBackend"
    assert events == [("_FailingBackend", "quota exceeded")]


def test_raises_last_error_when_every_backend_fails(tmp_path):
    chain = TtsFallbackProvider(
        [_FailingBackend(ValueError("first")), _FailingBackend(ValueError("second"))]
    )
    try:
        chain.synthesize("hello", tmp_path / "out.wav")
        assert False, "expected ValueError"
    except ValueError as e:
        assert str(e) == "second"


def test_requires_at_least_one_backend():
    try:
        TtsFallbackProvider([])
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_backend_chain_names(tmp_path):
    chain = TtsFallbackProvider([_StubBackend(), _StubBackend()])
    assert chain.backend_chain_names == ["_StubBackend", "_StubBackend"]
