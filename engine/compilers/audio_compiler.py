"""AudioCompiler - Screenplay -> narrated Audio Screenplay (.wav).
Strips scene-heading/action-line formatting into flowing narration text before TTS.
Registered in capability_registry as "narration" -> local execution (pyttsx3)."""
from __future__ import annotations

import re
import time
from pathlib import Path

from engine.compilers.base import CompilerBase, ValidationResult
from engine.kernel.models import Provenance
from engine.packs.capability_registry import resolve_capability

SCENE_HEADING_RE = re.compile(r"^(INT\.|EXT\.).*$", re.MULTILINE)


class AudioCompiler(CompilerBase):
    compiler_id = "audio_compiler"

    def __init__(self, tts_provider) -> None:
        self._tts = tts_provider
        self._capability = resolve_capability("narration")

    def validate(self, input_text: str) -> list[ValidationResult]:
        violations = []
        if not input_text.strip():
            violations.append("screenplay text is empty")
        return [ValidationResult(layer="structural", passed=not violations, violations=violations)]

    def _to_narration(self, screenplay_text: str) -> str:
        without_headings = SCENE_HEADING_RE.sub("", screenplay_text)
        lines = [ln.strip() for ln in without_headings.splitlines() if ln.strip()]
        return " ".join(lines)

    def generate(self, input_text: str) -> str:
        return self._to_narration(input_text)

    def run(self, screenplay_text: str, out_path: Path) -> tuple[Path, Provenance, dict]:
        results = self.validate(screenplay_text)
        if any(not r.passed for r in results):
            raise ValueError(f"Validation failed: {results}")
        narration = self.generate(screenplay_text)
        start = time.monotonic()
        result_path = self._tts.synthesize(narration, out_path)
        duration_s = time.monotonic() - start
        self.review(narration)
        provenance = self.export(
            knowledge_version="1.0", model=self._capability.provider_id, output_text=narration
        )
        metrics = self.build_metrics(
            duration_s=duration_s,
            tokens=len(narration.split()),
            model=self._capability.provider_id,
            confidence=0.8,
            provenance=provenance,
        )
        metrics["provider"] = self._capability.provider_id
        metrics["execution_mode"] = self._capability.execution_mode.value
        return result_path, provenance, metrics
