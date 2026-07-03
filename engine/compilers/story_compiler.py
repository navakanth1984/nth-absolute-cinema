"""StoryCompiler - Idea -> Story Bible. First creative stage of the Sprint 1 vertical
slice. Runs through LlmOrchestrator (retry + metrics), never a provider directly."""
from __future__ import annotations

from engine.compilers.base import CompilerBase, ValidationResult
from engine.kernel.models import Provenance
from engine.model_manager.orchestrator import LlmOrchestrator

SYSTEM_PROMPT = (
    "You are a story development assistant. Given a one-line creative idea, write a "
    "concise Story Bible in Markdown: Logline, Theme, Setting, Main Character, "
    "Central Conflict, Tone. Keep it under 400 words."
)


class StoryCompiler(CompilerBase):
    compiler_id = "story_compiler"

    def __init__(self, orchestrator: LlmOrchestrator) -> None:
        self._orchestrator = orchestrator

    def validate(self, input_text: str) -> list[ValidationResult]:
        violations = []
        if not input_text.strip():
            violations.append("idea_text is empty")
        return [ValidationResult(layer="structural", passed=not violations, violations=violations)]

    def generate(self, input_text: str) -> str:
        prompt = f"Idea: {input_text}\n\nWrite the Story Bible now."
        output, self._last_metrics = self._orchestrator.generate(prompt, system=SYSTEM_PROMPT)
        return output

    def run(self, idea_text: str) -> tuple[str, Provenance, dict]:
        results = self.validate(idea_text)
        if any(not r.passed for r in results):
            raise ValueError(f"Validation failed: {results}")
        output = self.generate(idea_text)
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
        return output, provenance, metrics
