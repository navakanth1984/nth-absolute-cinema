from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nac import Studio
from engine.model_manager.ollama_provider import OllamaNotReachableError, OllamaProvider


def _studio_autodetect(tmp_path, monkeypatch):
    monkeypatch.setenv("NAC_ROOT_OVERRIDE", str(tmp_path))
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    (tmp_path / ".nac-root").write_text("")
    # Force Ollama's generate() to fail deterministically regardless of whether
    # a real Ollama server happens to be running in this environment - this test
    # is about the fallback chain, not about live Ollama availability.
    monkeypatch.setattr(
        OllamaProvider,
        "generate",
        lambda self, prompt, system="": (_ for _ in ()).throw(OllamaNotReachableError("not running")),
    )
    return Studio(provider_override=None)


def test_autodetect_falls_through_to_mock_when_ollama_unreachable(tmp_path, monkeypatch):
    studio = _studio_autodetect(tmp_path, monkeypatch)
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
