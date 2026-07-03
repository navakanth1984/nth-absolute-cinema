"""KnowledgeRepo - MVP subset of KnowledgeGraphRepository (REPOSITORY_INTERFACES.md).
Sprint 1 scope only: Story node with idea/story_bible/screenplay/audio/prompt fields.
Beats, Scenes, Characters (full CREATIVE_GRAPH_SPEC.md sec 2) are Sprint 2+."""
from __future__ import annotations

import sqlite3
import uuid


class KnowledgeRepo:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def create_story(self, idea_text: str) -> str:
        story_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO story (id, idea_text) VALUES (?, ?)",
            (story_id, idea_text),
        )
        self._conn.commit()
        return story_id

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
