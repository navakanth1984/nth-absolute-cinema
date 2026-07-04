"""Offline TTS via pyttsx3 (Windows SAPI voices) - Sprint 1's TTS choice over Kokoro
(COMPUTE_MANAGER_SPEC.md on-demand install is a Sprint 2+ upgrade path for this)."""
import time
import wave
from pathlib import Path

import pyttsx3

from engine.model_manager.provider_protocol import VoiceRequest, VoiceResponse


def _get_wav_info(file_path: Path) -> tuple[float, int | None]:
    try:
        with wave.open(str(file_path), "rb") as wav:
            duration = wav.getnframes() / float(wav.getframerate())
            return duration, wav.getframerate()
    except Exception:
        return 0.0, None


class TtsProvider:
    def synthesize(self, request: str | VoiceRequest, out_path: Path) -> VoiceResponse:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        text = request.text if isinstance(request, VoiceRequest) else request

        start = time.monotonic()
        engine = pyttsx3.init()
        engine.save_to_file(text, str(out_path))
        engine.runAndWait()
        latency = time.monotonic() - start

        file_size = out_path.stat().st_size if out_path.is_file() else 0
        duration, sample_rate = _get_wav_info(out_path)

        return VoiceResponse(
            audio_path=out_path,
            provider="pyttsx3",
            voice="default",
            duration=duration,
            latency=latency,
            cost=0.0,
            credits_used=0,
            sample_rate=sample_rate,
            file_size=file_size,
        )

