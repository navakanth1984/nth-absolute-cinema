"""ElevenLabsProvider - Cloud Voice Provider integration for NAC.
Reads ELEVENLABS_API_KEY from .env; raises ElevenLabsNotConfiguredError if missing."""
from __future__ import annotations

import os
import time
from pathlib import Path
import wave
import requests
from typing import Any

from engine.model_manager.provider_protocol import VoiceRequest, VoiceResponse


class ElevenLabsNotConfiguredError(RuntimeError):
    pass


def write_pcm_to_wav(
    pcm_bytes: bytes,
    wav_path: Path,
    sample_rate: int = 24000,
    channels: int = 1,
    sample_width: int = 2,
) -> None:
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(wav_path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)


def estimate_duration(file_path: Path, output_format: str) -> float:
    if file_path.suffix.lower() == ".wav":
        try:
            with wave.open(str(file_path), "rb") as wav:
                return wav.getnframes() / float(wav.getframerate())
        except Exception:
            pass
    
    # Fallback to estimating based on MP3 bitrate
    if file_path.is_file():
        file_size = file_path.stat().st_size
        bitrate = 128  # default kbps for mp3_44100_128
        if "mp3_" in output_format:
            try:
                parts = output_format.split("_")
                if len(parts) >= 3:
                    bitrate = int(parts[2])
            except Exception:
                pass
        return file_size / (bitrate * 125.0)
    return 0.0


class ElevenLabsProvider:
    def __init__(
        self,
        voice_id: str = "pNInz6obpgq5qcGbe82y",  # default: Adam
        model: str = "eleven_multilingual_v2",
        base_url: str = "https://api.elevenlabs.io/v1",
        timeout_s: float = 30.0,
        api_key: str | None = None,
    ) -> None:
        self.voice_id = voice_id
        self.model = model
        self.base_url = base_url
        self.timeout_s = timeout_s
        self._api_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")
        if not self._api_key:
            raise ElevenLabsNotConfiguredError(
                "ELEVENLABS_API_KEY not set in environment - required to construct "
                "ElevenLabsProvider."
            )
        self.last_call_duration_s: float = 0.0

    def synthesize(self, request: str | VoiceRequest, out_path: Path) -> VoiceResponse:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 1. Parse request parameters
        if isinstance(request, VoiceRequest):
            text = request.text
            voice_id = request.voice_id or self.voice_id
            output_format = request.output_format
        else:
            text = request
            voice_id = self.voice_id
            output_format = None

        if not output_format:
            if out_path.suffix.lower() == ".mp3":
                output_format = "mp3_44100_128"
            else:
                output_format = "pcm_24000"

        # 2. Build API request body
        body: dict[str, Any] = {
            "text": text,
            "model_id": self.model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True,
            }
        }
        
        if isinstance(request, VoiceRequest) and request.style is not None:
            body["voice_settings"]["style"] = request.style

        # 3. Call ElevenLabs API
        start = time.monotonic()
        url = f"{self.base_url}/text-to-speech/{voice_id}"
        resp = requests.post(
            url,
            headers={
                "xi-api-key": self._api_key,
                "Content-Type": "application/json",
            },
            params={"output_format": output_format},
            json=body,
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        latency = time.monotonic() - start
        self.last_call_duration_s = latency

        audio_bytes = resp.content

        # 4. Save to output path, handling PCM to WAV conversion if needed
        if output_format.startswith("pcm_"):
            try:
                sample_rate = int(output_format.split("_")[1])
            except Exception:
                sample_rate = 24000
            write_pcm_to_wav(audio_bytes, out_path, sample_rate=sample_rate)
        else:
            out_path.write_bytes(audio_bytes)

        # 5. Extract audio metadata and metrics
        file_size = out_path.stat().st_size if out_path.is_file() else len(audio_bytes)
        duration = estimate_duration(out_path, output_format)
        
        # Calculate sample rate
        sample_rate = None
        if output_format.startswith("pcm_"):
            try:
                sample_rate = int(output_format.split("_")[1])
            except Exception:
                sample_rate = 24000
        elif "44100" in output_format:
            sample_rate = 44100
        elif "22050" in output_format:
            sample_rate = 22050
        elif "16000" in output_format:
            sample_rate = 16000
        elif "8000" in output_format:
            sample_rate = 8000

        credits_used = len(text)
        # ElevenLabs standard pricing: $0.15 per 1000 characters = $0.00015 per character
        cost = credits_used * 0.00015

        return VoiceResponse(
            audio_path=out_path,
            provider="ElevenLabs",
            voice=voice_id,
            duration=duration,
            latency=latency,
            cost=cost,
            credits_used=credits_used,
            sample_rate=sample_rate,
            file_size=file_size,
        )
