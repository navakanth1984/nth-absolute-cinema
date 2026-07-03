"""nac - the public NAC SDK. This is the ONLY module anything outside the
E:\\nth-absolute-cinema repository may import (MODULE_BOUNDARIES.md's engine.api
boundary rule, applied here for Sprint 1's SDK-shaped surface instead of a REST API).
Consumers (the CLI, agent_os/filmmaking/nac_bridge.py) see only Studio - never
engine.knowledge, engine.compilers, engine.storage, or engine.model_manager
directly. `from nac.compilers...` / `from nac.storage...` are never supported
imports - only `from nac import Studio, OllamaNotReachableError` is public API.

VERSIONED PUBLIC INTERFACE (as of Checkpoint C.5, 2026-07-03): from this point on,
`.nac`/Production Package layout, the Knowledge Graph schema (engine.storage.db.SCHEMA),
compiler contracts (engine.compilers.base.CompilerBase), and this Studio SDK's public
method signatures are treated as versioned interfaces - new fields/methods are
additive (backward compatible); removing or renaming an existing field/method is a
breaking change requiring a version bump (SDK_VERSION below), mirroring
VERSIONING_POLICY.md's semver rules for the frozen v1.0 specs. No such bump has
happened yet - SDK_VERSION 0.1.0 is Checkpoint C.5's baseline going forward.
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

SDK_VERSION = "0.1.0"

_repo_root = Path(__file__).resolve().parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from engine.kernel.paths import PathResolver
from engine.storage.db import init_db
from engine.storage.knowledge_repo import KnowledgeRepo
from engine.model_manager.ollama_provider import OllamaNotReachableError
from engine.model_manager.orchestrator import LlmOrchestrator
from engine.model_manager.resolver import resolve_provider
from engine.model_manager.tts_provider import TtsProvider
from engine.compilers.story_compiler import StoryCompiler
from engine.compilers.screenplay_compiler import ScreenplayCompiler
from engine.compilers.audio_compiler import AudioCompiler
from engine.compilers.prompt_compiler import PromptCompiler
from engine.portability.export import export_project
from engine.packs.capability_registry import CAPABILITY_REGISTRY

__all__ = ["Studio", "OllamaNotReachableError", "SDK_VERSION"]

_STAGE_DISPATCH = {
    "story": "generate_story",
    "screenplay": "generate_screenplay",
    "audio": "generate_audio",
    "prompt": "generate_prompt",
}


class Studio:
    """The NAC public SDK. One Studio instance = one Ollama model + one project DB.

    Checkpoint A status: create_project() is implemented and tested.
    generate_story/generate_screenplay/generate_audio/generate_prompt/export raise
    NotImplementedError until Checkpoints B/C add the compilers they depend on -
    each error names which checkpoint completes it, so a caller always knows what's
    real right now versus what's coming, rather than silently no-op-ing.
    """

    def __init__(self, model: str = "gemma2:9b", provider_override: str | None = None) -> None:
        """provider_override: "ollama" | "openrouter" | "mock" to bypass the
        auto-detection fallback chain (Ollama -> OpenRouter -> Mock). Compilers never
        see which provider was chosen - only Studio and resolve_provider() know."""
        resolver = PathResolver()
        start = Path(os.environ.get("NAC_ROOT_OVERRIDE", str(_repo_root)))
        self._root = resolver.find_root(start)
        self._resolver = resolver
        db_path = resolver.resolve("projects/mvp.db")
        self._conn = init_db(db_path)
        self._repo = KnowledgeRepo(self._conn)
        self._provider = resolve_provider(ollama_model=model, force=provider_override)
        self._orchestrator = LlmOrchestrator(self._provider)
        self._tts = TtsProvider()

    def create_project(self, idea_text: str, target_runtime_minutes: int = 15) -> str:
        return self._repo.create_story(idea_text, target_runtime_minutes=target_runtime_minutes)

    def generate_story(self, project_id: str) -> str:
        story = self._repo.get_story(project_id)
        bible_text, _, metrics = StoryCompiler(self._orchestrator).run(story["idea_text"])
        self._repo.save_story_bible(project_id, bible_text)
        self._repo.save_compiler_metrics(project_id, metrics["compiler"], metrics)
        return bible_text

    def generate_screenplay(self, project_id: str) -> str:
        story = self._repo.get_story(project_id)
        screenplay_text, _, metrics = ScreenplayCompiler(self._orchestrator).run(
            story["story_bible"], target_runtime_minutes=story["target_runtime_minutes"]
        )
        self._repo.save_screenplay(project_id, screenplay_text)
        self._repo.save_compiler_metrics(project_id, metrics["compiler"], metrics)
        return screenplay_text

    def generate_audio(self, project_id: str) -> Path:
        story = self._repo.get_story(project_id)
        audio_out = self._resolver.resolve(f"projects/{project_id}_audio.wav")
        audio_path, _, metrics = AudioCompiler(self._tts).run(story["screenplay"], audio_out)
        self._repo.save_audio_path(project_id, str(audio_path))
        self._repo.save_compiler_metrics(project_id, metrics["compiler"], metrics)
        return audio_path

    def generate_prompt(self, project_id: str) -> str:
        story = self._repo.get_story(project_id)
        prompt_text, _, metrics = PromptCompiler(self._orchestrator).run(story["screenplay"])
        self._repo.save_motion_poster_prompt(project_id, prompt_text)
        self._repo.save_compiler_metrics(project_id, metrics["compiler"], metrics)
        return prompt_text

    def export(self, project_id: str, out_dir: Path) -> Path:
        """Incremental by construction: exports whatever stages are populated right
        now (export_project handles None/missing fields), so a caller may export
        after any subset of stages - not only once all six are complete."""
        story = self._repo.get_story(project_id)
        metrics = self._repo.get_compiler_metrics(project_id)
        return export_project(story, metrics, Path(out_dir))

    def get_audio_path(self, project_id: str) -> Path | None:
        """Sprint 2A: read-only access to the saved audio file path, for the
        Director Studio's audio player - avoids the audio route reaching into
        KnowledgeRepo internals directly."""
        story = self._repo.get_story(project_id)
        return Path(story["audio_path"]) if story["audio_path"] else None

    def get_capabilities(self) -> list[dict]:
        """Sprint 2A: read-only passthrough of the Capability Registry (display
        only - no logic lives outside engine.packs.capability_registry) for the
        Director Studio's Providers panel. Honestly reports available=False
        entries (elevenlabs, google_flow_music) rather than hiding them."""
        return [
            {
                "capability": name,
                "provider_id": entry.provider_id,
                "execution_mode": entry.execution_mode.value,
                "available": entry.available,
            }
            for name, entry in CAPABILITY_REGISTRY.items()
        ]

    def get_provider_info(self) -> dict:
        """Sprint 2A: read-only passthrough for the Director Studio's Provider
        display field. Reports the LLM provider actually resolved for this Studio
        instance (Ollama/OpenRouter/Mock) - no execution-mode/GPU/credits data
        exists in the engine yet, so this stays a single honest field rather than
        inventing the rest of PROVIDER_ADAPTER_SPEC.md's future shape."""
        return {"llm_provider": type(self._provider).__name__}

    def list_projects(self) -> list[dict]:
        """Sprint 2A: passthrough to KnowledgeRepo.list_stories() for the Director
        Studio's Project Home - see that method's docstring for why this was
        missing until now."""
        return self._repo.list_stories()

    def get_metrics(self, project_id: str) -> list[dict]:
        """Sprint 2A: read-only passthrough to the compiler_metrics table already
        written by every generate_*() call, for the Director Studio's per-stage
        Metrics panel - previously recorded but never exposed through the SDK."""
        return self._repo.get_compiler_metrics(project_id)

    def get_status(self, project_id: str) -> dict:
        """Checkpoint C.5: partial-compilation support - shows which stages are
        populated so a caller can decide what to run next, rather than assuming the
        full six-step pipeline always runs in one shot."""
        return self._repo.get_status(project_id)

    def regenerate_stage(self, project_id: str, stage: str) -> str | Path:
        """Checkpoint C.5: targeted regeneration - re-runs exactly one stage
        ("story"|"screenplay"|"audio"|"prompt") against the project's current graph
        state, overwriting only that stage's saved output. This is the same
        generate_*() method a full pipeline run calls; the only thing new is naming
        it by stage string for CLI/caller convenience."""
        if stage not in _STAGE_DISPATCH:
            raise ValueError(f"Unknown stage '{stage}'. Valid stages: {list(_STAGE_DISPATCH)}")
        method = getattr(self, _STAGE_DISPATCH[stage])
        return method(project_id)

    def record_review(
        self, project_id: str, stage: str, verdict: str, comment: str | None = None
    ) -> None:
        """Checkpoint C.5: stage-by-stage director review. verdict is free-form but
        conventionally one of "approved"/"needs_revision"/"rejected", matching
        CREATIVE_GRAPH_SPEC.md sec 7's ReviewEntry.verdict values (full ReviewGraph
        persistence remains Sprint 2+; this is the Sprint 1 subset: a flat log per
        project, not a graph node)."""
        self._repo.record_review(project_id, stage, verdict, comment=comment)

    def get_reviews(self, project_id: str) -> list[dict]:
        return self._repo.get_reviews(project_id)

    def import_asset(self, project_id: str, capability: str, file_path: Path | str) -> str:
        """Checkpoint C.5: asset import for UI-only providers (Google Flow, Google
        Flow Music - capability_registry entries with execution_mode=UI). The
        workflow is: generate manually in the provider's UI -> download the file ->
        import_asset() hashes it and records it against this project, closing the
        loop between a prompt package NAC generated and the asset a human produced
        from it, without NAC needing a real API integration to that provider."""
        file_path = Path(file_path)
        if not file_path.is_file():
            raise FileNotFoundError(f"No file at {file_path} to import")
        content_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        return self._repo.import_asset(project_id, capability, str(file_path), content_hash)

    def get_assets(self, project_id: str) -> list[dict]:
        return self._repo.get_assets(project_id)

    def get_stage_content(self, project_id: str) -> dict:
        """Checkpoint C.5: public read-only access to each stage's current content,
        for a review UI (CLI's `nac review`, or a future GUI) to display without
        reaching into repo/storage internals directly."""
        story = self._repo.get_story(project_id)
        return {
            "story": story["story_bible"],
            "screenplay": story["screenplay"],
            "prompt": story["motion_poster_prompt"],
        }
