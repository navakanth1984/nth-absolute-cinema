from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nac import Studio


def test_diagnostics_voice_provider_reporting(tmp_path, monkeypatch):
    monkeypatch.setenv("NAC_ROOT_OVERRIDE", str(tmp_path))
    (tmp_path / ".nac-root").write_text("")

    # 1. Test when ElevenLabs API key is configured
    monkeypatch.setenv("ELEVENLABS_API_KEY", "key1")
    monkeypatch.setenv("SARVAM_API_KEY", "key2")

    studio = Studio()
    d = studio.get_diagnostics()

    assert d["elevenlabs"] == "configured"
    assert d["sarvam"] == "configured"
    assert d["provider"]["tts_provider"] == "ElevenLabsProvider"
    assert "ElevenLabsProvider" in d["provider"]["tts_fallback_chain"]
    assert "SarvamTtsProvider" in d["provider"]["tts_fallback_chain"]
    assert "TtsProvider" in d["provider"]["tts_fallback_chain"]

    # 2. Test when ElevenLabs is missing key
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    
    studio = Studio()
    d = studio.get_diagnostics()

    assert d["elevenlabs"] == "not configured"
    assert d["provider"]["tts_provider"] == "SarvamTtsProvider"
    assert "ElevenLabsProvider" not in d["provider"]["tts_fallback_chain"]
    assert "SarvamTtsProvider" in d["provider"]["tts_fallback_chain"]
