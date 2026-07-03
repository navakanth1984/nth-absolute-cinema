"""CompilerBase - COMPILER_ABI.md's 8-stage pipeline, MVP-scoped.

MVP simplifications (intentional, not omissions):
  - plan(): returns a rough Estimate from a word-count heuristic, not a calibrated
    model - COMPUTE_MANAGER_SPEC.md-integrated real estimation is Sprint 2+.
  - repair(): bounded to zero retries in Sprint 1 (a failed Measurement just fails
    the job) - real repair logic needs a defect taxonomy that doesn't exist yet.
  - review(): only ai_self_review is implemented (a trivial non-empty-output check);
    human_review (CREATIVE_GRAPH_SPEC.md sec 7 ReviewEntry, stage="human_review") is a
    Sprint 2+ UI concern - the CLI prints the artifact and the human reads it, which
    is the review, just not persisted as a ReviewEntry row yet.
Every subclass still implements validate/plan/generate/measure/repair/review/export
as real methods - none of these are stubs that silently no-op.

Structured metrics: every subclass's run() returns (output_text, Provenance,
metrics_dict) - a three-tuple. metrics_dict is produced by build_metrics() below and
travels alongside the artifact so future sessions can optimize compilers, compare
local vs cloud, benchmark models, and replay generations without changing any
compiler's core logic.
"""
from __future__ import annotations

import hashlib
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from engine.kernel.models import Estimate, Provenance


@dataclass
class ValidationResult:
    layer: str
    passed: bool
    violations: list[str]


class CompilerBase(ABC):
    compiler_id: str
    compiler_version: str = "0.1.0"
    abi_version: str = "1.0"

    @abstractmethod
    def validate(self, input_text: str) -> list[ValidationResult]:
        ...

    def plan(self, input_text: str) -> Estimate:
        approx_tokens = max(1, len(input_text.split()) * 2)
        return Estimate(
            job_id=str(uuid.uuid4()),
            estimated_tokens=approx_tokens,
            estimated_gpu_hours=0.0,
            estimated_ram_mb=512,
            estimated_time_s=max(5, approx_tokens // 20),
            estimated_cost_usd=0.0,
            confidence=0.3,
        )

    @abstractmethod
    def generate(self, input_text: str) -> str:
        ...

    def measure(self, output_text: str) -> dict:
        return {"output_chars": len(output_text), "output_words": len(output_text.split())}

    def repair(self, output_text: str, measurement: dict) -> str:
        return output_text

    def review(self, output_text: str) -> dict:
        passed = len(output_text.strip()) > 0
        return {"stage": "ai_self_review", "verdict": "approved" if passed else "rejected"}

    def export(self, knowledge_version: str, model: str, output_text: str) -> Provenance:
        output_hash = hashlib.sha256(output_text.encode("utf-8")).hexdigest()
        return Provenance(
            knowledge_version=knowledge_version,
            compiler_id=self.compiler_id,
            compiler_version=self.compiler_version,
            model=model,
            output_hash=output_hash,
        )

    def build_metrics(
        self,
        duration_s: float,
        tokens: int,
        model: str,
        confidence: float,
        provenance: Provenance,
        cost_usd: float = 0.0,
        warnings: list[str] | None = None,
        quality_score: float | None = None,
    ) -> dict:
        return {
            "compiler": self.compiler_id,
            "duration_s": round(duration_s, 3),
            "tokens": tokens,
            "model": model,
            "cost_usd": cost_usd,
            "confidence": confidence,
            "warnings": warnings or [],
            "quality_score": quality_score,
            "output_hash": provenance.output_hash,
            "knowledge_version": provenance.knowledge_version,
            "compiler_version": self.compiler_version,
        }


def timed_generate(compiler: "CompilerBase", provider, input_text: str) -> tuple[str, float]:
    """Helper: run generate() while timing it, for compilers whose provider doesn't
    self-report duration (e.g. TtsProvider). OllamaProvider self-reports via
    last_call_duration_s instead, used directly by LLM-backed compilers."""
    start = time.monotonic()
    output = compiler.generate(input_text)
    return output, time.monotonic() - start
