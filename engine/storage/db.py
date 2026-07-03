"""SQLite connection + schema init. Project-tier storage per WORKSPACE_SPEC.md -
this file only ever writes into the project tier, never cache/renders/temp."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS story (
    id TEXT PRIMARY KEY,
    idea_text TEXT NOT NULL,
    story_bible TEXT,
    screenplay TEXT,
    audio_path TEXT,
    motion_poster_prompt TEXT,
    graph_spec_version TEXT NOT NULL DEFAULT '1.0',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
