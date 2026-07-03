"""Offline TTS via pyttsx3 (Windows SAPI voices) - Sprint 1's TTS choice over Kokoro
(COMPUTE_MANAGER_SPEC.md on-demand install is a Sprint 2+ upgrade path for this)."""
from __future__ import annotations

from pathlib import Path

import pyttsx3


class TtsProvider:
    def synthesize(self, text: str, out_path: Path) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        engine = pyttsx3.init()
        engine.save_to_file(text, str(out_path))
        engine.runAndWait()
        return out_path
