"""KnowledgeRepo - MVP subset of KnowledgeGraphRepository (REPOSITORY_INTERFACES.md).
Sprint 1 scope only: Story node with idea/story_bible/screenplay/audio/prompt fields
plus target_runtime_minutes (the deterministic project constraint that drives
screenplay page-count via engine.kernel.runtime, per the Checkpoint B decision to
defer full Character/Scene/Beat graph population - Beats, Scenes, Characters, full
CREATIVE_GRAPH_SPEC.md sec 2, remain Sprint 2+). compiler_metrics is a first-class
table from Checkpoint B onward, not bolted on later."""
from __future__ import annotations

import json
import sqlite3
import uuid


class KnowledgeRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create_story(self, idea_text: str, target_runtime_minutes: int = 15) -> str:
        story_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO story (id, idea_text, target_runtime_minutes) VALUES (?, ?, ?)",
            (story_id, idea_text, target_runtime_minutes),
        )
        self._conn.commit()
        return story_id

    def save_compiler_metrics(self, story_id: str, compiler: str, metrics: dict) -> None:
        self._conn.execute(
            "INSERT INTO compiler_metrics (id, story_id, compiler, metrics_json) "
            "VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), story_id, compiler, json.dumps(metrics)),
        )
        self._conn.commit()

    def get_compiler_metrics(self, story_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT compiler, metrics_json, created_at FROM compiler_metrics "
            "WHERE story_id = ? ORDER BY created_at",
            (story_id,),
        ).fetchall()
        return [
            {"compiler": r["compiler"], "created_at": r["created_at"], **json.loads(r["metrics_json"])}
            for r in rows
        ]

    def get_story(self, story_id: str) -> dict:
        row = self._conn.execute(
            "SELECT * FROM story WHERE id = ?", (story_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"No story with id {story_id}")
        return dict(row)

    def save_story_bible(self, story_id: str, content: str) -> None:
        self._conn.execute(
            "UPDATE story SET story_bible = ? WHERE id = ?", (content, story_id)
        )
        self._conn.commit()

    def save_screenplay(self, story_id: str, fountain_text: str) -> None:
        self._conn.execute(
            "UPDATE story SET screenplay = ? WHERE id = ?", (fountain_text, story_id)
        )
        self._conn.commit()

    def save_audio_path(self, story_id: str, audio_path: str) -> None:
        self._conn.execute(
            "UPDATE story SET audio_path = ? WHERE id = ?", (audio_path, story_id)
        )
        self._conn.commit()

    def save_motion_poster_prompt(self, story_id: str, prompt_text: str) -> None:
        self._conn.execute(
            "UPDATE story SET motion_poster_prompt = ? WHERE id = ?",
            (prompt_text, story_id),
        )
        self._conn.commit()
