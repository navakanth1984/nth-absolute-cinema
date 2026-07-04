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
from datetime import datetime, timezone


class KnowledgeRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create_story(self, idea_text: str, target_runtime_minutes: int = 15) -> str:
        """created_at is generated here (microsecond ISO 8601) rather than left to
        SQLite's `datetime('now')` default, which only has second-level precision -
        two projects created in the same second would otherwise tie and sort
        arbitrarily in list_stories()."""
        story_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO story (id, idea_text, target_runtime_minutes, created_at) "
            "VALUES (?, ?, ?, ?)",
            (story_id, idea_text, target_runtime_minutes, created_at),
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
            "SELECT id, story_id, compiler, metrics_json, created_at FROM compiler_metrics "
            "WHERE story_id = ? ORDER BY created_at",
            (story_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "story_id": r["story_id"],
                "compiler": r["compiler"],
                "metrics_json": r["metrics_json"],
                "created_at": r["created_at"],
                **json.loads(r["metrics_json"]),
            }
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

    def list_stories(self) -> list[dict]:
        """Sprint 2A: project discovery for the Director Studio's Project Home -
        without this there is no way to enumerate existing projects (the CLI and
        Studio SDK previously assumed the caller already knew the project id)."""
        rows = self._conn.execute(
            "SELECT id, idea_text, target_runtime_minutes, story_bible, screenplay, "
            "audio_path, motion_poster_prompt, created_at FROM story "
            "ORDER BY created_at DESC"
        ).fetchall()
        return [
            {
                "id": r["id"],
                "idea_text": r["idea_text"],
                "target_runtime_minutes": r["target_runtime_minutes"],
                "created_at": r["created_at"],
                "story_bible": bool(r["story_bible"]),
                "screenplay": bool(r["screenplay"]),
                "audio": bool(r["audio_path"]),
                "motion_poster_prompt": bool(r["motion_poster_prompt"]),
            }
            for r in rows
        ]

    def get_status(self, story_id: str) -> dict:
        """Checkpoint C.5: which stages are populated for a project - the basis for
        partial-compilation/regeneration decisions (a caller checks status before
        deciding what to (re)generate, rather than always running all six steps)."""
        story = self.get_story(story_id)
        return {
            "story_id": story_id,
            "idea": bool(story["idea_text"]),
            "story_bible": bool(story["story_bible"]),
            "screenplay": bool(story["screenplay"]),
            "audio": bool(story["audio_path"]),
            "motion_poster_prompt": bool(story["motion_poster_prompt"]),
            "asset_count": len(self.get_assets(story_id)),
            "review_count": len(self.get_reviews(story_id)),
        }

    def record_review(
        self, story_id: str, stage: str, verdict: str, comment: str | None = None
    ) -> None:
        self._conn.execute(
            "INSERT INTO review_log (id, story_id, stage, verdict, comment) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), story_id, stage, verdict, comment),
        )
        self._conn.commit()

    def get_reviews(self, story_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, story_id, stage, verdict, comment, created_at FROM review_log "
            "WHERE story_id = ? ORDER BY created_at",
            (story_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def import_asset(
        self, story_id: str, capability: str, file_path: str, content_hash: str
    ) -> str:
        asset_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO assets (id, story_id, capability, file_path, content_hash) "
            "VALUES (?, ?, ?, ?, ?)",
            (asset_id, story_id, capability, file_path, content_hash),
        )
        self._conn.commit()
        return asset_id

    def get_assets(self, story_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT id, story_id, capability, file_path, content_hash, source, created_at "
            "FROM assets WHERE story_id = ? ORDER BY created_at",
            (story_id,),
        ).fetchall()
        return [dict(r) for r in rows]
