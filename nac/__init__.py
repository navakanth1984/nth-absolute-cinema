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
from engine.model_manager.ollama_provider import OllamaProvider, OllamaNotReachableError
from engine.model_manager.tts_provider import TtsProvider

__all__ = ["Studio", "OllamaNotReachableError"]


class Studio:
    """The NAC public SDK. One Studio instance = one Ollama model + one project DB.

    Checkpoint A status: create_project() is implemented and tested.
    generate_story/generate_screenplay/generate_audio/generate_prompt/export raise
    NotImplementedError until Checkpoints B/C add the compilers they depend on -
    each error names which checkpoint completes it, so a caller always knows what's
    real right now versus what's coming, rather than silently no-op-ing.
    """

    def __init__(self, model: str = "gemma2:9b") -> None:
        resolver = PathResolver()
        start = Path(os.environ.get("NAC_ROOT_OVERRIDE", str(_repo_root)))
        self._root = resolver.find_root(start)
        self._resolver = resolver
        db_path = resolver.resolve("projects/mvp.db")
        self._conn = init_db(db_path)
        self._repo = KnowledgeRepo(self._conn)
        self._provider = OllamaProvider(model=model)
        self._tts = TtsProvider()

    def create_project(self, idea_text: str) -> str:
        return self._repo.create_story(idea_text)

    def generate_story(self, project_id: str) -> str:
        raise NotImplementedError(
            "StoryCompiler not yet wired in - lands in Checkpoint B (Task 5)."
        )

    def generate_screenplay(self, project_id: str) -> str:
        raise NotImplementedError(
            "ScreenplayCompiler not yet wired in - lands in Checkpoint B (Task 6)."
        )

    def generate_audio(self, project_id: str) -> Path:
        raise NotImplementedError(
            "AudioCompiler not yet wired in - lands in Checkpoint C (Task 9)."
        )

    def generate_prompt(self, project_id: str) -> str:
        raise NotImplementedError(
            "PromptCompiler not yet wired in - lands in Checkpoint C (Task 10)."
        )

    def export(self, project_id: str, out_dir: Path) -> Path:
        raise NotImplementedError(
            "Export not yet wired in - lands in Checkpoint C (Task 11)."
        )
