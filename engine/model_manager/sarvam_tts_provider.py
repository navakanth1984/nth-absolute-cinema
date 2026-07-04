"""SarvamTtsProvider - cloud TTS backend via Sarvam AI's text-to-speech API, for
higher-quality/Indic-language narration than the offline pyttsx3 TtsProvider.
Reads SARVAM_API_KEY from the environment; raises loudly (not silently) if the
key is missing when this provider is explicitly constructed - same contract as
GeminiProvider/OpenRouterProvider.

Not registered as the default TTS backend: AudioCompiler is wired to a single
TtsProvider-shaped object today (see nac/__init__.py), so swapping this in is a
Studio-level fallback-chain decision, not something this class does on its own.
"""
import base64
import os
import time
import wave
from pathlib import Path

import requests

from engine.model_manager.provider_protocol import VoiceRequest, VoiceResponse


class SarvamNotConfiguredError(RuntimeError):
    pass


def _get_wav_info(file_path: Path) -> tuple[float, int | None]:
    try:
        with wave.open(str(file_path), "rb") as wav:
            duration = wav.getnframes() / float(wav.getframerate())
            return duration, wav.getframerate()
    except Exception:
        return 0.0, None


class SarvamTtsProvider:
    def __init__(
        self,
        target_language_code: str = "en-IN",
        speaker: str = "meera",
        base_url: str = "https://api.sarvam.ai",
        timeout_s: float = 60.0,
        api_key: str | None = None,
    ) -> None:
        self.target_language_code = target_language_code
        self.speaker = speaker
        self.base_url = base_url
        self.timeout_s = timeout_s
        self._api_key = api_key or os.environ.get("SARVAM_API_KEY", "")
        if not self._api_key:
            raise SarvamNotConfiguredError(
                "SARVAM_API_KEY not set in environment - required to construct "
                "SarvamTtsProvider."
            )
        self.last_call_duration_s: float = 0.0

    def synthesize(self, request: str | VoiceRequest, out_path: Path) -> VoiceResponse:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        if isinstance(request, VoiceRequest):
            text = request.text
            language = request.language or self.target_language_code
            speaker = request.voice_id or self.speaker
        else:
            text = request
            language = self.target_language_code
            speaker = self.speaker

        start = time.monotonic()
        resp = requests.post(
            f"{self.base_url}/text-to-speech",
            headers={"API-Subscription-Key": self._api_key},
            json={
                "inputs": [text],
                "target_language_code": language,
                "speaker": speaker,
            },
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        latency = time.monotonic() - start
        self.last_call_duration_s = latency
        
        data = resp.json()
        audios = data.get("audios") or []
        if not audios:
            raise RuntimeError("Sarvam TTS returned no audio in response")
        out_path.write_bytes(base64.b64decode(audios[0]))

        # Get audio info
        file_size = out_path.stat().st_size if out_path.is_file() else 0
        duration, sample_rate = _get_wav_info(out_path)
        credits_used = len(text)
        # Estimating Sarvam cost: e.g. 0.00008 per character (or 0.0)
        cost = credits_used * 0.00008

        return VoiceResponse(
            audio_path=out_path,
            provider="Sarvam",
            voice=speaker,
            duration=duration,
            latency=latency,
            cost=cost,
            credits_used=credits_used,
            sample_rate=sample_rate,
            file_size=file_size,
        )

