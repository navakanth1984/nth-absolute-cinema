# Local Provider Smoke Test Report

Generated: 2026-07-04T10:40:50.732468+00:00

Scope: local, zero-external-quota providers only. Gemini, Sarvam, and OpenRouter are deliberately NOT called here - see `scripts/gemini_sarvam_live_smoke_test.py` (not created until this report passes) for that gated follow-up.

**Readiness score: 100.0% (8 passed / 0 skipped / 0 failed / 8 total)**

## Checks

### MockProvider baseline inference — PASSED (0.0s)
- **provider**: MockProvider
- **status**: Available
- **total_response_time_s**: 0.0
- **tokens_generated**: 41
- **tokens_per_sec**: not measurable (in-process call completed in <1ms)
- **peak_memory_mb**: 31.612928
- **startup_latency_s**: N/A - MockProvider has no startup phase
- **first_token_latency_s**: N/A - generate() is non-streaming, only total response time is measurable
- **sample_output**: [MOCK OUTPUT seed=2a6d4c73] Generated response for prompt of 77 chars under system context of 0 chars. This is determini

### Ollama detection + inference (if available) — PASSED (3.032s)
- **provider**: Ollama
- **status**: Not Installed / Not Running

### pyttsx3 offline TTS synthesis — PASSED (0.437s)
- **provider**: pyttsx3 (offline TTS)
- **status**: Available
- **total_response_time_s**: 0.421
- **audio_duration_s**: 1.99
- **sample_rate_hz**: 22050
- **file_size_bytes**: 87826
- **temp_file_cleaned_up**: True

### No-network-egress guarantee (Mock + pyttsx3) — PASSED (0.484s)
- **result**: No network calls made by MockProvider or pyttsx3 TtsProvider

### LLM FallbackProvider routing - generic primitive (no network) — PASSED (0.0s)
- **chain**: ['_FailingProvider', 'MockProvider']
- **routed_around**: ['_FailingProvider']
- **active**: MockProvider

### TTS TtsFallbackProvider routing - generic primitive (no network) — PASSED (0.235s)
- **chain**: ['_FailingTtsBackend', 'TtsProvider']
- **routed_around**: ['_FailingTtsBackend']
- **active**: TtsProvider

### Studio orchestrator local-only routing - real production code path — PASSED (3.062s)
- **method_under_test**: Studio._build_fallback_chain() - the real production code path, not a stand-in FallbackProvider
- **resulting_chain_with_cloud_keys_removed**: ['MockProvider']
- **verdict**: Correctly excludes Gemini/OpenRouter and falls through to MockProvider when no cloud keys are present

### Timeout / cancellation handling (hard deadline) — PASSED (0.219s)
- **elapsed_s**: 0.22
- **events**: [('_SlowLocalProvider', 'ProviderTimeoutError')]
- **verdict**: Deadline enforced correctly

## Not Integrated In This Repo (honest scope, not a failure)

- **llama.cpp / GGUF**: No provider class in engine/model_manager implements this.
- **ONNX Runtime**: No provider class in engine/model_manager implements this.
- **Local HuggingFace Transformers**: No provider class in engine/model_manager implements this.
- **AgentOS-specific local routers (navakanth001/agent_os)**: MODULE_BOUNDARIES.md forbids engine.model_manager importing across repos; ollama_provider.py already reimplements the one pattern (Ollama HTTP client) that was shared, standalone.

## Suggested Next Steps

- Ollama is not running - install from ollama.com and `ollama serve` to exercise the local-LLM path (Gemma/DeepSeek/etc via `ollama pull <model>`).
- All local checks passed. Safe to proceed with one gated live Gemini + Sarvam smoke test when approved.