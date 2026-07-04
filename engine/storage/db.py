"""SQLite connection + schema init. Project-tier storage per WORKSPACE_SPEC.md -
this file only ever writes into the project tier, never cache/renders/temp."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS story (
    id TEXT PRIMARY KEY,
    idea_text TEXT NOT NULL,
    target_runtime_minutes INTEGER NOT NULL DEFAULT 15,
    story_bible TEXT,
    screenplay TEXT,
    audio_path TEXT,
    motion_poster_prompt TEXT,
    graph_spec_version TEXT NOT NULL DEFAULT '1.0',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS compiler_metrics (
    id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL REFERENCES story(id),
    compiler TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS review_log (
    id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL REFERENCES story(id),
    stage TEXT NOT NULL,
    verdict TEXT NOT NULL,
    comment TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL REFERENCES story(id),
    capability TEXT NOT NULL,
    file_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual_import',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def init_db(db_path: Path) -> sqlite3.Connection:
    """check_same_thread=False: Sprint 2A's dashboard server holds one Studio (and
    therefore one connection) for the process lifetime, but FastAPI dispatches sync
    route handlers to a threadpool - a new thread per request. sqlite3 still
    serializes actual access internally, so this is safe for our single-connection,
    no-concurrent-write-conflict usage; it does not change on-disk format or SQL."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
