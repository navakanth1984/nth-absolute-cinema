"""SarvamTtsProvider - cloud TTS backend via Sarvam AI's text-to-speech API, for
higher-quality/Indic-language narration than the offline pyttsx3 TtsProvider.
Reads SARVAM_API_KEY from the environment; raises loudly (not silently) if the
key is missing when this provider is explicitly constructed - same contract as
GeminiProvider/OpenRouterProvider.

Not registered as the default TTS backend: AudioCompiler is wired to a single
TtsProvider-shaped object today (see nac/__init__.py), so swapping this in is a
Studio-level fallback-chain decision, not something this class does on its own.
"""
from __future__ import annotations

import base64
import os
import time
from pathlib import Path

import requests


class SarvamNotConfiguredError(RuntimeError):
    pass


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

    def synthesize(self, text: str, out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        start = time.monotonic()
        resp = requests.post(
            f"{self.base_url}/text-to-speech",
            headers={"API-Subscription-Key": self._api_key},
            json={
                "inputs": [text],
                "target_language_code": self.target_language_code,
                "speaker": self.speaker,
            },
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        self.last_call_duration_s = time.monotonic() - start
        data = resp.json()
        audios = data.get("audios") or []
        if not audios:
            raise RuntimeError("Sarvam TTS returned no audio in response")
        out_path.write_bytes(base64.b64decode(audios[0]))
        return out_path
