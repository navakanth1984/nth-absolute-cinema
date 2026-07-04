"""Local Provider Smoke Test report generator (feat/provider-orchestration).

Runs a real (but 100% local, zero-external-quota) check of every provider this
repo's engine.model_manager actually implements, and writes a human-readable
report to wiki/local-provider-smoke-report.md. Deliberately does NOT call
Gemini, Sarvam, or OpenRouter - this is the free/local gate that must pass
before spending any real cloud quota (see
wiki/sprint3a5-phase1-findings.md-adjacent Director Experience Pass 1 work for
the same "verify before trusting" discipline applied to the backend instead of
the UI).

Usage: py -3.12 scripts/local_provider_smoke_test.py
"""
from __future__ import annotations

import sys
import time
import traceback
import wave
from datetime import datetime, timezone
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_repo_root))

import requests

from engine.model_manager.fallback_provider import FallbackProvider
from engine.model_manager.mock_provider import MockProvider
from engine.model_manager.tts_fallback_provider import TtsFallbackProvider
from engine.model_manager.tts_provider import TtsProvider

OLLAMA_URL = "http://localhost:11434"
TINY_PROMPT = "Write a two-line cinematic scene where a traveler enters an abandoned temple."

NOT_INTEGRATED = [
    ("llama.cpp / GGUF", "No provider class in engine/model_manager implements this."),
    ("ONNX Runtime", "No provider class in engine/model_manager implements this."),
    ("Local HuggingFace Transformers", "No provider class in engine/model_manager implements this."),
    (
        "AgentOS-specific local routers (navakanth001/agent_os)",
        "MODULE_BOUNDARIES.md forbids engine.model_manager importing across "
        "repos; ollama_provider.py already reimplements the one pattern (Ollama "
        "HTTP client) that was shared, standalone.",
    ),
]

try:
    import psutil
    _HAVE_PSUTIL = True
except ImportError:
    _HAVE_PSUTIL = False


def _peak_memory_mb() -> float | None:
    if not _HAVE_PSUTIL:
        return None
    try:
        return psutil.Process().memory_info().rss / 1e6
    except Exception:
        return None


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


def check(name: str, fn) -> dict:
    """Runs one check, capturing pass/fail/skip + timing + any exception text."""
    start = time.monotonic()
    try:
        result = fn()
        elapsed = time.monotonic() - start
        if result is None:
            return {"name": name, "status": "SKIPPED", "elapsed_s": round(elapsed, 3), "detail": None}
        return {"name": name, "status": "PASSED", "elapsed_s": round(elapsed, 3), "detail": result}
    except Exception as e:  # noqa: BLE001 - a smoke test must never crash the report itself
        elapsed = time.monotonic() - start
        return {
            "name": name,
            "status": "FAILED",
            "elapsed_s": round(elapsed, 3),
            "detail": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc(),
        }


def check_mock_provider() -> dict:
    provider = MockProvider()
    mem_before = _peak_memory_mb()
    start = time.monotonic()
    output = provider.generate(TINY_PROMPT)
    elapsed = time.monotonic() - start
    mem_after = _peak_memory_mb()
    assert "MOCK OUTPUT" in output
    return {
        "provider": "MockProvider",
        "status": "Available",
        "total_response_time_s": round(elapsed, 4),
        "tokens_generated": provider.last_call_tokens,
        "tokens_per_sec": (
            round(provider.last_call_tokens / elapsed, 1)
            if elapsed > 0.001
            else "not measurable (in-process call completed in <1ms)"
        ),
        "peak_memory_mb": mem_after if mem_after is not None else "unavailable (psutil not installed)",
        "startup_latency_s": "N/A - MockProvider has no startup phase",
        "first_token_latency_s": "N/A - generate() is non-streaming, only total response time is measurable",
        "sample_output": output[:120],
    }


def check_ollama() -> dict | None:
    reachable = _ollama_reachable()
    if not reachable:
        return {"provider": "Ollama", "status": "Not Installed / Not Running"}
    models = _ollama_models()
    if not models:
        return {"provider": "Ollama", "status": "Model Missing (Ollama running, no models pulled)"}

    from engine.model_manager.ollama_provider import OllamaProvider

    model = models[0]
    provider = OllamaProvider(model=model)
    start = time.monotonic()
    output = provider.generate(TINY_PROMPT)
    elapsed = time.monotonic() - start
    tokens = provider.last_call_tokens
    return {
        "provider": f"Ollama ({model})",
        "status": "Available",
        "installed_models": models,
        "total_response_time_s": round(elapsed, 3),
        "tokens_generated": tokens,
        "tokens_per_sec": round(tokens / max(elapsed, 1e-6), 1),
        "startup_latency_s": "N/A - Ollama's /api/generate is non-streaming here, model load time (if any) is folded into total_response_time_s",
        "first_token_latency_s": "N/A - OllamaProvider uses stream=False; would require switching to streaming mode to measure",
        "sample_output": output[:120],
    }


def check_pyttsx3_tts() -> dict:
    provider = TtsProvider()
    out_path = _repo_root / "temp" / "smoke_test_narration.wav"
    start = time.monotonic()
    provider.synthesize("A short cinematic test line.", out_path)
    elapsed = time.monotonic() - start
    with wave.open(str(out_path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        duration_s = frames / float(rate) if rate else 0.0
    size_bytes = out_path.stat().st_size
    out_path.unlink()
    return {
        "provider": "pyttsx3 (offline TTS)",
        "status": "Available",
        "total_response_time_s": round(elapsed, 3),
        "audio_duration_s": round(duration_s, 2),
        "sample_rate_hz": rate,
        "file_size_bytes": size_bytes,
        "temp_file_cleaned_up": not out_path.exists(),
    }


def check_no_network_egress() -> dict:
    def _blow_up(*args, **kwargs):
        raise AssertionError("network call attempted during local-only check")

    orig_get, orig_post = requests.get, requests.post
    requests.get = _blow_up
    requests.post = _blow_up
    try:
        MockProvider().generate(TINY_PROMPT)
        tmp = _repo_root / "temp" / "smoke_no_network.wav"
        TtsProvider().synthesize("no network here", tmp)
        tmp.unlink()
    finally:
        requests.get, requests.post = orig_get, orig_post
    return {"result": "No network calls made by MockProvider or pyttsx3 TtsProvider"}


class _FailingProvider:
    model = "failing-provider"
    last_call_duration_s = 0.0
    last_call_tokens = 0

    def generate(self, prompt: str, system: str = "") -> str:
        raise RuntimeError("simulated local model failure")


class _FailingTtsBackend:
    def synthesize(self, text: str, out_path: Path) -> Path:
        raise RuntimeError("simulated local TTS failure")


def check_llm_routing() -> dict:
    """Generic-primitive check: proves FallbackProvider itself routes around a
    failing provider. This does NOT exercise Studio._build_fallback_chain() -
    see check_orchestrator_local_only_routing() below for that."""
    events = []
    chain = FallbackProvider(
        [_FailingProvider(), MockProvider()], on_fallback=lambda p, e: events.append(type(p).__name__)
    )
    chain.generate(TINY_PROMPT)
    assert chain.active_provider_name == "MockProvider"
    return {"chain": chain.provider_chain_names, "routed_around": events, "active": chain.active_provider_name}


def check_orchestrator_local_only_routing() -> dict:
    """Exercises the REAL Studio._build_fallback_chain() (the actual new
    orchestrator code from this session), forced into local-only mode by
    removing GEMINI_API_KEY/OPENROUTER_API_KEY for the duration of the check -
    not a stand-in FallbackProvider built from scratch. This is what proves
    "ProviderOrchestrator selects the correct provider according to routing
    policy" for local-only mode, specifically."""
    import os as _os

    from nac import Studio

    saved = {k: _os.environ.pop(k, None) for k in ("GEMINI_API_KEY", "OPENROUTER_API_KEY")}
    try:
        studio = Studio()
        chain_names = studio._provider.provider_chain_names
    finally:
        for k, v in saved.items():
            if v is not None:
                _os.environ[k] = v

    assert "GeminiProvider" not in chain_names, "local-only mode must exclude Gemini"
    assert "OpenRouterProvider" not in chain_names, "local-only mode must exclude OpenRouter"
    assert chain_names[-1] == "MockProvider", "chain must always end in a guaranteed-success provider"
    return {
        "method_under_test": "Studio._build_fallback_chain() - the real production code path, "
        "not a stand-in FallbackProvider",
        "resulting_chain_with_cloud_keys_removed": chain_names,
        "verdict": "Correctly excludes Gemini/OpenRouter and falls through to MockProvider "
        "when no cloud keys are present",
    }


def check_tts_routing() -> dict:
    events = []
    chain = TtsFallbackProvider(
        [_FailingTtsBackend(), TtsProvider()], on_fallback=lambda b, e: events.append(type(b).__name__)
    )
    out = _repo_root / "temp" / "smoke_routing.wav"
    chain.synthesize("routing check", out)
    out.unlink()
    return {"chain": chain.backend_chain_names, "routed_around": events, "active": chain.active_backend_name}


def check_timeout_handling() -> dict:
    """Reuses FallbackProvider's hard wall-clock deadline mechanism (already unit
    -tested in tests/test_fallback_provider.py) to confirm a hung local provider
    doesn't block the whole chain - this is the exact bug class (a provider's own
    internal timeout not covering total call duration) that motivated
    FallbackProvider's deadline in the first place."""

    class _SlowLocalProvider:
        model = "slow-local"
        timeout_s = 0.2
        last_call_duration_s = 0.0
        last_call_tokens = 0

        def generate(self, prompt: str, system: str = "") -> str:
            time.sleep(5.0)
            return "unreachable"

    events = []
    chain = FallbackProvider(
        [_SlowLocalProvider(), MockProvider()],
        on_fallback=lambda p, e: events.append((type(p).__name__, type(e).__name__)),
    )
    start = time.monotonic()
    chain.generate(TINY_PROMPT)
    elapsed = time.monotonic() - start
    assert elapsed < 2.0, "hard deadline did not fire in time"
    return {"elapsed_s": round(elapsed, 2), "events": events, "verdict": "Deadline enforced correctly"}


def main() -> None:
    checks = [
        ("MockProvider baseline inference", check_mock_provider),
        ("Ollama detection + inference (if available)", check_ollama),
        ("pyttsx3 offline TTS synthesis", check_pyttsx3_tts),
        ("No-network-egress guarantee (Mock + pyttsx3)", check_no_network_egress),
        ("LLM FallbackProvider routing - generic primitive (no network)", check_llm_routing),
        ("TTS TtsFallbackProvider routing - generic primitive (no network)", check_tts_routing),
        ("Studio orchestrator local-only routing - real production code path", check_orchestrator_local_only_routing),
        ("Timeout / cancellation handling (hard deadline)", check_timeout_handling),
    ]

    results = [check(name, fn) for name, fn in checks]

    passed = sum(1 for r in results if r["status"] == "PASSED")
    skipped = sum(1 for r in results if r["status"] == "SKIPPED")
    failed = sum(1 for r in results if r["status"] == "FAILED")
    total = len(results)
    readiness_score = round(100 * passed / total, 1)

    lines: list[str] = []
    lines.append("# Local Provider Smoke Test Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append(
        "Scope: local, zero-external-quota providers only. Gemini, Sarvam, and "
        "OpenRouter are deliberately NOT called here - see "
        "`scripts/gemini_sarvam_live_smoke_test.py` (not created until this report "
        "passes) for that gated follow-up."
    )
    lines.append("")
    lines.append(f"**Readiness score: {readiness_score}% ({passed} passed / {skipped} skipped / {failed} failed / {total} total)**")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for r in results:
        lines.append(f"### {r['name']} — {r['status']} ({r['elapsed_s']}s)")
        if r["status"] == "FAILED":
            lines.append(f"```\n{r['detail']}\n{r.get('traceback', '')}\n```")
        elif r["detail"] is not None:
            for k, v in r["detail"].items():
                lines.append(f"- **{k}**: {v}")
        lines.append("")

    lines.append("## Not Integrated In This Repo (honest scope, not a failure)")
    lines.append("")
    for name, reason in NOT_INTEGRATED:
        lines.append(f"- **{name}**: {reason}")
    lines.append("")

    lines.append("## Suggested Next Steps")
    lines.append("")
    if failed:
        lines.append("- Fix the FAILED check(s) above before running the live Gemini/Sarvam smoke test.")
    ollama_result = next(r for r in results if r["name"].startswith("Ollama"))
    if ollama_result["detail"] and ollama_result["detail"].get("status", "").startswith("Not Installed"):
        lines.append("- Ollama is not running - install from ollama.com and `ollama serve` to exercise the local-LLM path (Gemma/DeepSeek/etc via `ollama pull <model>`).")
    elif ollama_result["detail"] and ollama_result["detail"].get("status", "").startswith("Model Missing"):
        lines.append("- Ollama is running but no models are pulled - `ollama pull gemma3:4b` (or your preferred local model) to exercise real local inference.")
    if not failed:
        lines.append("- All local checks passed. Safe to proceed with one gated live Gemini + Sarvam smoke test when approved.")

    report = "\n".join(lines)
    print(report)

    out_path = _repo_root / "wiki" / "local-provider-smoke-report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"\n\nReport written to {out_path}")


if __name__ == "__main__":
    main()
