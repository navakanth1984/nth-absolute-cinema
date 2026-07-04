from pathlib import Path
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.model_manager.elevenlabs_provider import (
    ElevenLabsProvider,
    ElevenLabsNotConfiguredError,
)
from engine.model_manager.provider_protocol import VoiceRequest


def test_raises_when_no_api_key(monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    try:
        ElevenLabsProvider(api_key=None)
        assert False, "expected ElevenLabsNotConfiguredError"
    except ElevenLabsNotConfiguredError:
        pass


def test_synthesize_writes_audio_file(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "fake-elevenlabs-key")
    provider = ElevenLabsProvider()

    fake_audio_bytes = b"fake-mp3-audio-content"
    fake_response = MagicMock()
    fake_response.content = fake_audio_bytes
    fake_response.raise_for_status.return_value = None

    out_path = tmp_path / "nested" / "out.mp3"
    with patch("requests.post", return_value=fake_response) as mock_post:
        response = provider.synthesize("Hello ElevenLabs", out_path)

    assert response.audio_path == out_path
    assert response.provider == "ElevenLabs"
    assert response.voice == "pNInz6obpgq5qcGbe82y"
    assert out_path.read_bytes() == fake_audio_bytes
    assert response.credits_used == len("Hello ElevenLabs")
    assert response.cost == len("Hello ElevenLabs") * 0.00015
    assert response.sample_rate == 44100
    assert response.file_size == len(fake_audio_bytes)
    assert response.duration > 0.0

    mock_post.assert_called_once()
    headers = mock_post.call_args.kwargs["headers"]
    assert headers["xi-api-key"] == "fake-elevenlabs-key"
    params = mock_post.call_args.kwargs["params"]
    assert params["output_format"] == "mp3_44100_128"


def test_synthesize_with_voice_request_customizations(monkeypatch, tmp_path):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "fake-elevenlabs-key")
    provider = ElevenLabsProvider()

    fake_audio_bytes = b"fake-pcm-audio-content"
    fake_response = MagicMock()
    fake_response.content = fake_audio_bytes
    fake_response.raise_for_status.return_value = None

    out_path = tmp_path / "out.wav"
    request = VoiceRequest(
        text="Hello customized world",
        voice_id="custom-voice-id",
        style=0.8,
        output_format="pcm_24000",
    )

    with patch("requests.post", return_value=fake_response) as mock_post:
        response = provider.synthesize(request, out_path)

    assert response.audio_path == out_path
    assert response.voice == "custom-voice-id"
    assert response.sample_rate == 24000

    # Verify requests.post payload
    url = mock_post.call_args.args[0]
    assert "custom-voice-id" in url
    body = mock_post.call_args.kwargs["json"]
    assert body["voice_settings"]["style"] == 0.8
    params = mock_post.call_args.kwargs["params"]
    assert params["output_format"] == "pcm_24000"
