from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import requests

from nac import Studio
from engine.model_manager.ollama_provider import OllamaNotReachableError, OllamaProvider


def test_autodetect_skips_ollama_when_preflight_unreachable(tmp_path, monkeypatch):
    """No real Ollama server in the test environment -> the fast reachability
    preflight (Sprint 2A.2) should skip Ollama entirely rather than adding it to
    the chain and letting a later generate() call hang on its 120s timeout."""
    monkeypatch.setenv("NAC_ROOT_OVERRIDE", str(tmp_path))
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    (tmp_path / ".nac-root").write_text("")

    def _unreachable(*a, **kw):
        raise requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(requests, "get", _unreachable)
    studio = Studio(provider_override=None)
    pid = studio.create_project("An idea")

    bible = studio.generate_story(pid)

    assert "MOCK OUTPUT" in bible
    info = studio.get_provider_info()
    assert info["llm_provider"] == "MockProvider"
    assert info["fallback_chain"] == ["MockProvider"]  # Ollama never added, no API key configured
    assert info["fallback_events"] == []  # nothing to skip - Mock was the only candidate


def test_autodetect_falls_through_to_mock_when_ollama_reachable_but_generation_fails(tmp_path, monkeypatch):
    """Ollama passes the reachability preflight (e.g. server up but the specific
    model isn't pulled) - the chain should still fall through to Mock on the
    actual generate() failure, and record the fallback event."""
    monkeypatch.setenv("NAC_ROOT_OVERRIDE", str(tmp_path))
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    (tmp_path / ".nac-root").write_text("")

    class _FakeResponse:
        status_code = 200

    monkeypatch.setattr(requests, "get", lambda *a, **kw: _FakeResponse())
    monkeypatch.setattr(
        OllamaProvider,
        "generate",
        lambda self, prompt, system="": (_ for _ in ()).throw(OllamaNotReachableError("model not pulled")),
    )
    studio = Studio(provider_override=None)
    pid = studio.create_project("An idea")

    bible = studio.generate_story(pid)

    assert "MOCK OUTPUT" in bible
    info = studio.get_provider_info()
    assert info["llm_provider"] == "MockProvider"
    assert info["fallback_chain"] == ["OllamaProvider", "MockProvider"]
    assert len(info["fallback_events"]) == 1
    assert info["fallback_events"][0]["skipped_provider"] == "OllamaProvider"


def test_explicit_override_bypasses_fallback_chain(tmp_path, monkeypatch):
    monkeypatch.setenv("NAC_ROOT_OVERRIDE", str(tmp_path))
    (tmp_path / ".nac-root").write_text("")
    studio = Studio(provider_override="mock")

    info = studio.get_provider_info()
    assert info["llm_provider"] == "MockProvider"
    assert info["fallback_chain"] is None  # not wrapped - force= pins to exactly one provider


def test_diagnostics_reports_real_values(tmp_path, monkeypatch):
    monkeypatch.setenv("NAC_ROOT_OVERRIDE", str(tmp_path))
    (tmp_path / ".nac-root").write_text("")
    studio = Studio(provider_override="mock")

    d = studio.get_diagnostics()
    assert d["sqlite"] == "ok"
    assert d["sdk_version"]
    assert d["python_version"]
    assert d["ollama"] in ("reachable", "unreachable")
    assert d["openrouter"] in ("configured", "not configured")
    assert d["gpu"]  # either a real name or "unknown" - never empty/missing
    assert isinstance(d["capabilities"], list)
