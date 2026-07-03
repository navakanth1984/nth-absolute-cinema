"""PromptCompiler - Screenplay -> Motion Poster prompt (Google Flow style).
Registered in capability_registry as "motion_poster" -> UI execution: this compiler's
output is a prompt PACKAGE meant for manual paste into Google Flow's UI, not an API
call - NAC has no Google Flow API integration, and the capability registry records
that honestly (execution_mode=UI) rather than pretending it's automated.

MVP: single hardcoded PlatformTarget (16:9), no full pack discovery (PACK_ABI.md's
CapabilityMatrix/Validator/Templates machinery is Sprint 2+)."""
from __future__ import annotations

from engine.compilers.base import CompilerBase, ValidationResult
from engine.kernel.models import Provenance
from engine.model_manager.orchestrator import LlmOrchestrator
from engine.packs.capability_registry import resolve_capability

SYSTEM_PROMPT = (
    "You are a visual prompt engineer for AI image/video generation. Given a "
    "screenplay excerpt, write ONE vivid, cinematic image-generation prompt "
    "describing the poster's key visual moment: subject, setting, lighting, mood, "
    "camera framing. One paragraph, no scene-heading jargon. End with the aspect "
    "ratio '16:9'."
)

ASPECT_RATIO = "16:9"


class PromptCompiler(CompilerBase):
    compiler_id = "prompt_compiler"
    pack_id_mvp = "google_flow_mvp"
    pack_version_mvp = "0.1.0"

    def __init__(self, orchestrator: LlmOrchestrator) -> None:
        self._orchestrator = orchestrator
        self._capability = resolve_capability("motion_poster")

    def validate(self, input_text: str) -> list[ValidationResult]:
        violations = []
        if not input_text.strip():
            violations.append("screenplay text is empty")
        return [ValidationResult(layer="structural", passed=not violations, violations=violations)]

    def generate(self, input_text: str) -> str:
        prompt = f"Screenplay excerpt:\n{input_text}\n\nWrite the motion poster prompt now."
        output, self._last_metrics = self._orchestrator.generate(prompt, system=SYSTEM_PROMPT)
        return output

    def run(self, screenplay_text: str) -> tuple[str, Provenance, dict]:
        results = self.validate(screenplay_text)
        if any(not r.passed for r in results):
            raise ValueError(f"Validation failed: {results}")
        output = self.generate(screenplay_text)
        if ASPECT_RATIO not in output:
            output = f"{output}\n\naspect_ratio: {ASPECT_RATIO}"
        output = self.repair(output, self.measure(output))
        self.review(output)
        provenance = self.export(
            knowledge_version="1.0", model=self._orchestrator.model, output_text=output
        )
        provenance.pack_id = self.pack_id_mvp
        provenance.pack_version = self.pack_version_mvp
        metrics = self.build_metrics(
            duration_s=self._last_metrics["duration_s"],
            tokens=self._last_metrics["tokens"],
            model=self._orchestrator.model,
            confidence=0.5,
            provenance=provenance,
        )
        metrics["provider"] = self._last_metrics["provider"]
        metrics["execution_mode"] = self._capability.execution_mode.value
        metrics["target_provider"] = self._capability.provider_id
        return output, provenance, metrics
