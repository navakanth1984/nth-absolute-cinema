"""nac - the public NAC SDK. This is the ONLY module anything outside the
E:\\nth-absolute-cinema repository may import (MODULE_BOUNDARIES.md's engine.api
boundary rule, applied here for Sprint 1's SDK-shaped surface instead of a REST API).
Consumers (the CLI, agent_os/filmmaking/nac_bridge.py) see only Studio - never
engine.knowledge, engine.compilers, engine.storage, or engine.model_manager
directly. `from nac.compilers...` / `from nac.storage...` are never supported
imports - only `from nac import Studio, OllamaNotReachableError` is public API.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

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

__all__ = ["Studio", "OllamaNotReachableError"]


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
        story = self._repo.get_story(project_id)
        metrics = self._repo.get_compiler_metrics(project_id)
        return export_project(story, metrics, Path(out_dir))
