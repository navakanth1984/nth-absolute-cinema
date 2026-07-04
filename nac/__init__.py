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
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import requests

SDK_VERSION = "0.1.0"

_repo_root = Path(__file__).resolve().parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from engine.kernel.paths import PathResolver
from engine.storage.db import init_db
from engine.storage.knowledge_repo import KnowledgeRepo
from engine.model_manager.fallback_provider import FallbackProvider
from engine.model_manager.mock_provider import MockProvider
from engine.model_manager.ollama_provider import OllamaNotReachableError, OllamaProvider
from engine.model_manager.openrouter_provider import (
    OpenRouterNotConfiguredError,
    OpenRouterProvider,
)
from engine.model_manager.orchestrator import LlmOrchestrator
from engine.model_manager.resolver import resolve_provider
from engine.model_manager.tts_provider import TtsProvider
from engine.compilers.story_compiler import StoryCompiler
from engine.compilers.screenplay_compiler import ScreenplayCompiler
from engine.compilers.audio_compiler import AudioCompiler
from engine.compilers.prompt_compiler import PromptCompiler
from engine.portability.export import export_project
from engine.portability.snapshot import Snapshot, SnapshotManifest, SnapshotManager
from engine.packs.capability_registry import CAPABILITY_REGISTRY

__all__ = [
    "Studio",
    "OllamaNotReachableError",
    "SDK_VERSION",
    "Snapshot",
    "SnapshotManifest",
    "SnapshotManager",
]

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
        auto-detection fallback chain and pin to exactly that provider (used by
        tests and explicit CLI --provider flags - no runtime fallback in this mode,
        matching resolve_provider()'s existing documented contract).

        provider_override=None (the default, used by `nac studio`/`nac create`
        with no flag): builds a FallbackProvider trying Ollama -> OpenRouter ->
        MockProvider *at every generate() call*, not just once at construction.
        Sprint 2A.1: a mid-session OpenRouter 429 (free-tier rate limit) used to
        fail the whole pipeline even though MockProvider was always available as
        a last resort - this makes that fallback actually happen, and records
        each fallback event so the caller/UI can be told a provider was skipped."""
        resolver = PathResolver()
        start = Path(os.environ.get("NAC_ROOT_OVERRIDE", str(_repo_root)))
        self._root = resolver.find_root(start)
        self._resolver = resolver
        db_path = resolver.resolve("projects/mvp.db")
        self._conn = init_db(db_path)
        self._repo = KnowledgeRepo(self._conn)
        self.last_fallback_events: list[dict] = []
        if provider_override is not None:
            self._provider = resolve_provider(ollama_model=model, force=provider_override)
        else:
            self._provider = self._build_fallback_chain(model)
        self._orchestrator = LlmOrchestrator(self._provider)
        self._tts = TtsProvider()

    def _build_fallback_chain(self, model: str) -> FallbackProvider:
        """Sprint 2A.2 fix: OllamaProvider's default generate() timeout is 120s
        and OpenRouterProvider's is 90s - fine for a deliberately-chosen provider,
        but disastrous here, where an unreachable Ollama used to make every
        generate() call hang for up to two minutes before even trying the next
        provider in the chain (observed live: an 8+ minute stall on a single
        click). A fast reachability preflight (same pattern as resolver.py's
        _ollama_reachable) skips Ollama entirely when it's not actually running,
        and the fallback-chain's OpenRouter instance gets a much shorter timeout
        than the default, since MockProvider is always one hop away as an
        instant, guaranteed-to-succeed last resort."""
        providers: list = []
        try:
            if requests.get("http://localhost:11434/api/tags", timeout=1.5).status_code == 200:
                providers.append(OllamaProvider(model=model))
        except requests.RequestException:
            pass  # Ollama not reachable - skip it instead of letting generate() hang on it
        try:
            providers.append(OpenRouterProvider(timeout_s=15.0))
        except OpenRouterNotConfiguredError:
            pass  # no API key configured - Mock is still in the chain
        providers.append(MockProvider())

        def on_fallback(provider, error: Exception) -> None:
            self.last_fallback_events.append(
                {"skipped_provider": type(provider).__name__, "error": str(error)}
            )

        return FallbackProvider(providers, on_fallback=on_fallback)

    def create_project(self, idea_text: str, target_runtime_minutes: int = 15) -> str:
        return self._repo.create_story(idea_text, target_runtime_minutes=target_runtime_minutes)

    def create_demo_project(self) -> str:
        """Sprint 2A.2: seeds a bundled sample project (nac/demo_content.py) with
        the Story Bible and Screenplay stages pre-filled - static text, not LLM
        output, so a fresh install has something explorable with zero network
        calls and zero generation cost. Audio/Motion Poster stay ungenerated so
        the demo still demonstrates the review->generate workflow, not just a
        read-only artifact."""
        from nac.demo_content import DEMO_IDEA, DEMO_SCREENPLAY, DEMO_STORY_BIBLE

        project_id = self.create_project(DEMO_IDEA, target_runtime_minutes=15)
        self._repo.save_story_bible(project_id, DEMO_STORY_BIBLE)
        self._repo.save_screenplay(project_id, DEMO_SCREENPLAY)
        return project_id

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

    def get_diagnostics(self) -> dict:
        """Sprint 2A.1: honest system-status snapshot for the Director Studio's
        Diagnostics panel. Every field here is a real, live-checked value - no
        placeholder/fabricated fields (no "GPU: RX5500M" unless a real GPU query
        actually returns that name; unreachable/undetectable fields report
        "unknown" or "not configured", never a guessed value)."""
        ollama_reachable = False
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=1.5)
            ollama_reachable = resp.status_code == 200
        except requests.RequestException:
            ollama_reachable = False

        try:
            self._conn.execute("SELECT 1").fetchone()
            sqlite_ok = True
        except Exception:
            sqlite_ok = False

        try:
            usage = shutil.disk_usage(self._root)
            disk = {"free_gb": round(usage.free / 1e9, 1), "total_gb": round(usage.total / 1e9, 1)}
        except OSError:
            disk = None

        gpu_name = "unknown"
        nvidia_smi = shutil.which("nvidia-smi")
        if nvidia_smi:
            try:
                out = subprocess.run(
                    [nvidia_smi, "--query-gpu=name", "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=3,
                )
                if out.returncode == 0 and out.stdout.strip():
                    gpu_name = out.stdout.strip().splitlines()[0]
            except (subprocess.SubprocessError, OSError):
                gpu_name = "unknown"

        return {
            "python_version": platform.python_version(),
            "sdk_version": SDK_VERSION,
            "sqlite": "ok" if sqlite_ok else "error",
            "ollama": "reachable" if ollama_reachable else "unreachable",
            "openrouter": "configured" if os.environ.get("OPENROUTER_API_KEY") else "not configured",
            "disk": disk,
            "gpu": gpu_name,
            "capabilities": self.get_capabilities(),
            "provider": self.get_provider_info(),
        }

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
        inventing the rest of PROVIDER_ADAPTER_SPEC.md's future shape.

        Sprint 2A.1: when running the auto-detect fallback chain, "llm_provider"
        reports whichever provider actually served the LAST successful call (not
        just the first in the chain), plus any fallback events recorded since
        this Studio was constructed."""
        if isinstance(self._provider, FallbackProvider):
            return {
                "llm_provider": self._provider.active_provider_name,
                "fallback_chain": self._provider.provider_chain_names,
                "fallback_events": list(self.last_fallback_events),
            }
        return {"llm_provider": type(self._provider).__name__, "fallback_chain": None, "fallback_events": []}

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
