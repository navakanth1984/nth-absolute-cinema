"""ScreenplayCompiler - Story Bible -> Screenplay (Fountain-ish plain text).
Target page count is driven by the project's target_runtime_minutes constraint
(engine.kernel.runtime.estimate_page_range) rather than hardcoded - the same
compiler targets a 15-minute short today and a feature length later by changing
that constraint, not by rewriting this prompt."""
from __future__ import annotations

from engine.compilers.base import CompilerBase, ValidationResult
from engine.kernel.models import Provenance
from engine.kernel.runtime import estimate_page_range
from engine.model_manager.orchestrator import LlmOrchestrator


class ScreenplayCompiler(CompilerBase):
    compiler_id = "screenplay_compiler"

    def __init__(self, orchestrator: LlmOrchestrator) -> None:
        self._orchestrator = orchestrator

    def validate(self, input_text: str) -> list[ValidationResult]:
        violations = []
        if not input_text.strip():
            violations.append("story_bible text is empty")
        return [ValidationResult(layer="structural", passed=not violations, violations=violations)]

    def _system_prompt(self, target_runtime_minutes: int) -> str:
        low, high = estimate_page_range(target_runtime_minutes)
        return (
            "You are a screenwriter. Given a Story Bible, write a screenplay "
            f"targeting a {target_runtime_minutes}-minute runtime (roughly {low}-{high} "
            "screenplay pages worth of scene content - write as much of it as you can "
            "in this response). Use standard screenplay format: scene headings in ALL "
            "CAPS (INT./EXT. LOCATION - TIME), action lines, character names centered "
            "before dialogue."
        )

    def generate(self, input_text: str, target_runtime_minutes: int = 15) -> str:
        prompt = f"Story Bible:\n{input_text}\n\nWrite the screenplay now."
        output, self._last_metrics = self._orchestrator.generate(
            prompt, system=self._system_prompt(target_runtime_minutes)
        )
        return output

    def run(self, story_bible_text: str, target_runtime_minutes: int = 15) -> tuple[str, Provenance, dict]:
        results = self.validate(story_bible_text)
        if any(not r.passed for r in results):
            raise ValueError(f"Validation failed: {results}")
        output = self.generate(story_bible_text, target_runtime_minutes)
        output = self.repair(output, self.measure(output))
        self.review(output)
        provenance = self.export(
            knowledge_version="1.0", model=self._orchestrator.model, output_text=output
        )
        metrics = self.build_metrics(
            duration_s=self._last_metrics["duration_s"],
            tokens=self._last_metrics["tokens"],
            model=self._orchestrator.model,
            confidence=0.6,
            provenance=provenance,
        )
        metrics["provider"] = self._last_metrics["provider"]
        metrics["attempts"] = self._last_metrics["attempts"]
        metrics["target_runtime_minutes"] = target_runtime_minutes
        return output, provenance, metrics
