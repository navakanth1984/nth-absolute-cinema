"""Extension-point interfaces for Phase 2+ subsystems. NONE of these are implemented
or wired into Sprint 1's pipeline - they exist so a future session can implement one
without redesigning anything upstream. Each raises NotImplementedError with a note on
what real requirements would drive the implementation; nothing here is called by
Studio, any compiler, or the CLI in Sprint 1.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class CreditEstimator(ABC):
    """Phase 2+: track/estimate remaining credits per paid provider (Google Flow,
    Google Flow Music, ElevenLabs character quota, OpenRouter balance). Local
    providers (Ollama, MockProvider) always report unlimited."""

    @abstractmethod
    def remaining_credits(self, provider_id: str) -> float | None:
        """Returns None for unlimited/local providers, else a numeric balance."""
        raise NotImplementedError("CreditEstimator is a Phase 2+ extension point.")


class ProviderAdapter(ABC):
    """Phase 2+: standard interface every provider integration (local, API, or
    UI-package-generating) implements, so ExecutionMode dispatch is uniform. Sprint
    1's OllamaProvider/OpenRouterProvider/MockProvider satisfy LlmProvider directly
    instead - this ABC is for the broader multi-modal (image/audio/video) case."""

    @abstractmethod
    def execute(self, capability: str, payload: dict) -> dict:
        raise NotImplementedError("ProviderAdapter is a Phase 2+ extension point.")


class CreativeExecutionPlanner(ABC):
    """Phase 2+: sits above Model Manager, decides which workflow/provider/execution
    mode a high-level user request ("generate the teaser") should be broken into,
    optimizing for cost/time/quality against project goals. Sprint 1 has no such
    planner - Studio's methods are called directly, one stage at a time, by the CLI
    or a caller."""

    @abstractmethod
    def plan(self, user_request: str, project_id: str) -> list[dict]:
        raise NotImplementedError("CreativeExecutionPlanner is a Phase 2+ extension point.")


class FeedbackEngine(ABC):
    """Phase 2+: records per-artifact user rating, accept/reject, edit time, and
    regeneration count, without changing the frozen Knowledge Graph schema
    (CREATIVE_GRAPH_SPEC.md v1.0) - foundation for Phase 2's Director Memory /
    Experience Graph (see nac-phase2-future-directions memory)."""

    @abstractmethod
    def record_feedback(self, artifact_id: str, rating: int | None, accepted: bool | None) -> None:
        raise NotImplementedError("FeedbackEngine is a Phase 2+ extension point.")
