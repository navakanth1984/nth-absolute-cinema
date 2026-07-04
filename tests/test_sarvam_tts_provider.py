import base64
from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.model_manager.sarvam_tts_provider import (
    SarvamTtsProvider,
    SarvamNotConfiguredError,
)


def test_raises_when_no_api_key(monkeypatch):
    monkeypatch.delenv("SARVAM_API_KEY", raising=False)
    try:
        SarvamTtsProvider(api_key=None)
        assert False, "expected SarvamNotConfiguredError"
    except SarvamNotConfiguredError:
        pass


def test_synthesize_writes_decoded_audio(monkeypatch, tmp_path):
    monkeypatch.setenv("SARVAM_API_KEY", "fake-key")
    provider = SarvamTtsProvider()

    fake_audio_bytes = b"RIFF....WAVEfake"
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "audios": [base64.b64encode(fake_audio_bytes).decode("ascii")]
    }
    fake_response.raise_for_status.return_value = None
    out_path = tmp_path / "nested" / "out.wav"
    with patch("requests.post", return_value=fake_response) as mock_post:
        result = provider.synthesize("Hello world", out_path)

    assert result == out_path
    assert out_path.read_bytes() == fake_audio_bytes
    headers = mock_post.call_args.kwargs["headers"]
    assert headers["API-Subscription-Key"] == "fake-key"


def test_synthesize_raises_when_no_audio_returned(monkeypatch, tmp_path):
    monkeypatch.setenv("SARVAM_API_KEY", "fake-key")
    provider = SarvamTtsProvider()

    fake_response = MagicMock()
    fake_response.json.return_value = {"audios": []}
    fake_response.raise_for_status.return_value = None
    with patch("requests.post", return_value=fake_response):
        try:
            provider.synthesize("Hello", tmp_path / "out.wav")
            assert False, "expected RuntimeError"
        except RuntimeError:
            pass
