from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nac import Studio
from engine.model_manager.elevenlabs_provider import ElevenLabsProvider, ElevenLabsNotConfiguredError
from engine.model_manager.sarvam_tts_provider import SarvamTtsProvider, SarvamNotConfiguredError
from engine.model_manager.tts_provider import TtsProvider
from engine.model_manager.tts_fallback_provider import TtsFallbackProvider


def test_voice_fallback_chain_construction(monkeypatch):
    # Case 1: All API keys present
    monkeypatch.setenv("ELEVENLABS_API_KEY", "key1")
    monkeypatch.setenv("SARVAM_API_KEY", "key2")
    studio = Studio()
    assert studio._tts.backend_chain_names == ["ElevenLabsProvider", "SarvamTtsProvider", "TtsProvider"]

    # Case 2: Only ElevenLabs present
    monkeypatch.setenv("ELEVENLABS_API_KEY", "key1")
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    studio = Studio()
    assert studio._tts.backend_chain_names == ["ElevenLabsProvider", "TtsProvider"]

    # Case 3: Only Sarvam present
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.setenv("SARVAM_API_KEY", "key2")
    studio = Studio()
    assert studio._tts.backend_chain_names == ["SarvamTtsProvider", "TtsProvider"]

    # Case 4: No cloud keys
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    studio = Studio()
    assert studio._tts.backend_chain_names == ["TtsProvider"]


def test_voice_fallback_runtime_failure(monkeypatch, tmp_path):
    # Setup chain with failing ElevenLabs and working pyttsx3
    monkeypatch.setenv("ELEVENLABS_API_KEY", "key1")
    
    # Mock requests.post to fail for ElevenLabs
    fake_response = MagicMock()
    fake_response.raise_for_status.side_effect = RuntimeError("Rate Limit Exceeded")
    
    studio = Studio(voice_override="elevenlabs")
    # Make sure we fallback
    elevenlabs = studio._tts._backends[0]
    
    # Construct a real chain: ElevenLabs (mocked to fail) -> TtsProvider (working)
    local_tts = TtsProvider()
    chain = TtsFallbackProvider([elevenlabs, local_tts], on_fallback=studio._build_tts_chain()._on_fallback)
    
    out_path = tmp_path / "out.wav"
    with patch("requests.post", side_effect=RuntimeError("rate limit")):
        res = chain.synthesize("test text", out_path)
    
    # Should fallback to pyttsx3 and complete successfully
    assert res.provider == "pyttsx3"
    assert out_path.is_file()
    
    # Check that fallback event was recorded
    assert len(studio.last_tts_fallback_events) > 0
    assert studio.last_tts_fallback_events[0]["skipped_backend"] == "ElevenLabsProvider"
