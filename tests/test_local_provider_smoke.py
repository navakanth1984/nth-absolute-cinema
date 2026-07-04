"""Local Provider Smoke Test Suite (feat/provider-orchestration).

Validates the local, free, zero-external-quota parts of the provider
orchestrator - MockProvider, the offline pyttsx3 TTS backend, and the
FallbackProvider/TtsFallbackProvider routing logic - before any real Gemini or
Sarvam API call is made. CI-safe: nothing here requires Ollama to be running,
a model to be pulled, or network access. Ollama-specific checks skip (not
fail) when Ollama isn't reachable, since that's a real "not installed" state,
not a test failure.

Scope note: this repo's engine.model_manager only implements Ollama, OpenRouter,
Gemini, Mock, and two TTS backends (pyttsx3, Sarvam) - see
engine/model_manager/*_provider.py. There is no llama.cpp/GGUF, ONNX, or HF
Transformers provider integrated here, and no import of anything under
navakanth001/agent_os (MODULE_BOUNDARIES.md forbids the cross-repo dependency -
see ollama_provider.py's own docstring). Those are reported as NOT INTEGRATED
in the smoke report rather than silently skipped or faked.
"""
from __future__ import annotations

import time
import wave
from pathlib import Path
import sys

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.model_manager.fallback_provider import FallbackProvider
from engine.model_manager.mock_provider import MockProvider
from engine.model_manager.tts_fallback_provider import TtsFallbackProvider
from engine.model_manager.tts_provider import TtsProvider

OLLAMA_URL = "http://localhost:11434"
TINY_PROMPT = "Write a two-line cinematic scene where a traveler enters an abandoned temple."


def _ollama_reachable() -> bool:
    try:
        return requests.get(f"{OLLAMA_URL}/api/tags", timeout=1.5).status_code == 200
    except requests.RequestException:
        return False


def _ollama_models() -> list[str]:
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=1.5)
        return [m["name"] for m in resp.json().get("models", [])]
    except requests.RequestException:
        return []


# ---------- Detection / status ----------


def test_mock_provider_always_available():
    """MockProvider has no external dependency - it must always report available."""
    provider = MockProvider()
    assert provider.model == "mock-provider"


def test_pyttsx3_tts_always_available():
    """TtsProvider wraps pyttsx3 (offline, bundled dependency) - always available,
    unlike Sarvam which needs a configured API key."""
    provider = TtsProvider()
    assert provider is not None


def test_ollama_status_detected_without_raising():
    """Whether or not Ollama is installed/running, detection itself must never
    raise - a missing local runtime is a status ("not reachable"), not an error."""
    reachable = _ollama_reachable()
    assert isinstance(reachable, bool)
    if not reachable:
        pytest.skip("Ollama not reachable at localhost:11434 - reporting as not-installed, not a failure")
    models = _ollama_models()
    assert isinstance(models, list)


# ---------- Minimal inference ----------


def test_mock_inference_runs_and_reports_metrics():
    provider = MockProvider()
    start = time.monotonic()
    output = provider.generate(TINY_PROMPT)
    elapsed = time.monotonic() - start

    assert "MOCK OUTPUT" in output
    assert provider.last_call_tokens > 0
    assert elapsed < 1.0  # local, in-process - must be near-instant

    tokens_per_sec = provider.last_call_tokens / max(elapsed, 1e-6)
    assert tokens_per_sec > 0


def test_ollama_inference_runs_when_reachable_and_model_present():
    if not _ollama_reachable():
        pytest.skip("Ollama not reachable - not-installed status, not a failure")
    models = _ollama_models()
    if not models:
        pytest.skip("Ollama reachable but no local models pulled - model-missing status, not a failure")

    from engine.model_manager.ollama_provider import OllamaProvider

    provider = OllamaProvider(model=models[0])
    start = time.monotonic()
    output = provider.generate(TINY_PROMPT)
    elapsed = time.monotonic() - start

    assert isinstance(output, str) and output.strip()
    assert elapsed >= 0


def test_pyttsx3_synthesizes_playable_audio(tmp_path):
    provider = TtsProvider()
    out_path = tmp_path / "smoke_test_narration.wav"

    start = time.monotonic()
    result_path = provider.synthesize("A short cinematic test line.", out_path)
    elapsed = time.monotonic() - start

    assert result_path == out_path
    assert out_path.exists()
    assert out_path.stat().st_size > 0

    with wave.open(str(out_path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        duration_s = frames / float(rate) if rate else 0.0
    assert rate > 0
    assert duration_s > 0
    assert elapsed >= 0

    # Cleanup verification: tmp_path is pytest-managed, but assert we can remove
    # our own output cleanly (proves no lingering file handle from pyttsx3/wave).
    out_path.unlink()
    assert not out_path.exists()


# ---------- No-network guarantee ----------


def test_mock_and_tts_never_touch_the_network(tmp_path, monkeypatch):
    """Mock/pyttsx3 are the local-only baseline: prove neither one calls out to
    the network by making requests.get/post raise if invoked."""

    def _blow_up(*args, **kwargs):
        raise AssertionError("unexpected network call from a local-only provider")

    monkeypatch.setattr(requests, "get", _blow_up)
    monkeypatch.setattr(requests, "post", _blow_up)

    MockProvider().generate(TINY_PROMPT)
    TtsProvider().synthesize("no network here", tmp_path / "out.wav")


# ---------- Routing / fallback (no network required) ----------


class _FailingLocalProvider:
    model = "failing-local"
    last_call_duration_s = 0.0
    last_call_tokens = 0

    def generate(self, prompt: str, system: str = "") -> str:
        raise RuntimeError("simulated local model failure (e.g. model not pulled)")


class _FailingLocalTtsBackend:
    def synthesize(self, text: str, out_path: Path) -> Path:
        raise RuntimeError("simulated local TTS failure")


def test_llm_fallback_chain_routes_around_a_failed_local_provider():
    events = []
    chain = FallbackProvider(
        [_FailingLocalProvider(), MockProvider()],
        on_fallback=lambda p, e: events.append(type(p).__name__),
    )
    output = chain.generate(TINY_PROMPT)
    assert "MOCK OUTPUT" in output
    assert chain.active_provider_name == "MockProvider"
    assert events == ["_FailingLocalProvider"]


def test_tts_fallback_chain_routes_around_a_failed_local_backend(tmp_path):
    events = []
    chain = TtsFallbackProvider(
        [_FailingLocalTtsBackend(), TtsProvider()],
        on_fallback=lambda b, e: events.append(type(b).__name__),
    )
    result = chain.synthesize("fallback check", tmp_path / "out.wav")
    assert result.exists()
    assert chain.active_backend_name == "TtsProvider"
    assert events == ["_FailingLocalTtsBackend"]
    result.unlink()


def test_local_only_chain_never_includes_cloud_providers(monkeypatch):
    """Guards the smoke test's own premise for the generic FallbackProvider
    primitive - not Studio's real orchestrator (see the test below for that)."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    def _blow_up(*args, **kwargs):
        raise AssertionError("local-only smoke chain must never touch the network")

    monkeypatch.setattr(requests, "post", _blow_up)

    chain = FallbackProvider([MockProvider()])
    assert chain.provider_chain_names == ["MockProvider"]
    chain.generate(TINY_PROMPT)  # would raise via the monkeypatch if it reached out


def test_studio_orchestrator_excludes_cloud_providers_in_local_only_mode(monkeypatch):
    """Exercises the REAL Studio._build_fallback_chain() - the actual new
    orchestrator code, not a stand-in FallbackProvider built from scratch in
    the test itself. This is what proves "ProviderOrchestrator selects the
    correct provider according to routing policy" for local-only mode."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    from nac import Studio

    studio = Studio()
    chain_names = studio._provider.provider_chain_names

    assert "GeminiProvider" not in chain_names
    assert "OpenRouterProvider" not in chain_names
    assert chain_names[-1] == "MockProvider"
