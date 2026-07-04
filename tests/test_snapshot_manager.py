import sqlite3
import time
import uuid
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from engine.storage.knowledge_repo import KnowledgeRepo
from engine.portability.snapshot import Snapshot, SnapshotManifest, SnapshotManager


@pytest.fixture
def clean_conn() -> sqlite3.Connection:
    """Create a clean in-memory SQLite database initialized with the schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from engine.storage.db import SCHEMA
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def populate_demo_project(conn: sqlite3.Connection, project_id: str) -> None:
    """Helper to populate a test database with project details using SQL directly."""
    created_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO story (id, idea_text, target_runtime_minutes, story_bible, screenplay, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (project_id, "A cinematic space odyssey.", 15, "World rules...", "SCENE 1: Space...", created_at),
    )

    # 2 Metrics
    conn.execute(
        "INSERT INTO compiler_metrics (id, story_id, compiler, metrics_json, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), project_id, "story", '{"tokens": 120, "time_s": 1.2}', created_at),
    )
    conn.execute(
        "INSERT INTO compiler_metrics (id, story_id, compiler, metrics_json, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), project_id, "screenplay", '{"tokens": 450, "time_s": 3.4}', created_at),
    )

    # 2 Reviews
    conn.execute(
        "INSERT INTO review_log (id, story_id, stage, verdict, comment, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), project_id, "story", "approved", "Excellent universe concept.", created_at),
    )
    conn.execute(
        "INSERT INTO review_log (id, story_id, stage, verdict, comment, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), project_id, "screenplay", "rejected", "Needs more suspense.", created_at),
    )

    # 2 Assets
    conn.execute(
        "INSERT INTO assets (id, story_id, capability, file_path, content_hash, source, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), project_id, "audio", "projects/audio.wav", "a" * 64, "compiler", created_at),
    )
    conn.execute(
        "INSERT INTO assets (id, story_id, capability, file_path, content_hash, source, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), project_id, "image", "projects/poster.png", "b" * 64, "manual_import", created_at),
    )
    conn.commit()


class TestSnapshotManager:
    """Test suite for Snapshot model and SnapshotManager."""

    def test_empty_project_snapshot(self, clean_conn: sqlite3.Connection) -> None:
        manager = SnapshotManager()
        repo = KnowledgeRepo(clean_conn)
        project_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        # Insert a bare story row (no metrics, assets, or reviews)
        clean_conn.execute(
            "INSERT INTO story (id, idea_text, created_at) VALUES (?, ?, ?)",
            (project_id, "A lone warrior's quest.", created_at),
        )
        clean_conn.commit()

        snapshot = manager.create_snapshot(repo, project_id)

        assert snapshot.manifest.project_id == project_id
        assert snapshot.story["idea_text"] == "A lone warrior's quest."
        assert len(snapshot.compiler_metrics) == 0
        assert len(snapshot.review_log) == 0
        assert len(snapshot.assets) == 0
        assert snapshot.genomes == {}

        # Compliance checks
        assert manager.validate_snapshot(snapshot) == []
        assert manager.verify_snapshot(snapshot) is True

    def test_populated_project_snapshot(self, clean_conn: sqlite3.Connection) -> None:
        manager = SnapshotManager()
        repo = KnowledgeRepo(clean_conn)
        project_id = str(uuid.uuid4())
        populate_demo_project(clean_conn, project_id)

        snapshot = manager.create_snapshot(
            repo,
            project_id,
            compiler_versions={"story": "1.0.0"},
            pack_versions={"flow": "1.2.0"},
            provider_metadata={"provider": "mock"},
            environment_metadata={"os": "Windows"},
            runtime_config={"profile": "Standard"},
        )

        assert snapshot.manifest.project_id == project_id
        assert snapshot.manifest.engine_version == "0.1.0"
        assert snapshot.manifest.sdk_version == "0.1.0"
        assert snapshot.manifest.graph_spec_version == "1.2"
        assert snapshot.manifest.genome_spec_version == "1.2"
        assert snapshot.manifest.compiler_versions == {"story": "1.0.0"}
        assert snapshot.manifest.pack_versions == {"flow": "1.2.0"}
        assert snapshot.manifest.provider_metadata == {"provider": "mock"}
        assert snapshot.manifest.environment_metadata == {"os": "Windows"}
        assert snapshot.manifest.runtime_config == {"profile": "Standard"}
        assert len(snapshot.compiler_metrics) == 2
        assert len(snapshot.review_log) == 2
        assert len(snapshot.assets) == 2

        # Verify hierarchical hashes are set
        assert "story" in snapshot.manifest.component_hashes
        assert "compiler_metrics" in snapshot.manifest.component_hashes
        assert "review_log" in snapshot.manifest.component_hashes
        assert "assets" in snapshot.manifest.component_hashes
        assert "genomes" in snapshot.manifest.component_hashes

        assert manager.validate_snapshot(snapshot) == []
        assert manager.verify_snapshot(snapshot) is True

    def test_deterministic_snapshots(self, clean_conn: sqlite3.Connection) -> None:
        manager = SnapshotManager()
        repo = KnowledgeRepo(clean_conn)
        project_id = str(uuid.uuid4())
        populate_demo_project(clean_conn, project_id)

        snap1 = manager.create_snapshot(repo, project_id)
        snap2 = manager.create_snapshot(repo, project_id)

        # Core data hashes must be identical since database content is identical
        assert snap1.manifest.data_hash == snap2.manifest.data_hash
        assert snap1.manifest.component_hashes == snap2.manifest.component_hashes
        assert snap1.story == snap2.story
        assert snap1.compiler_metrics == snap2.compiler_metrics
        assert snap1.review_log == snap2.review_log
        assert snap1.assets == snap2.assets

        # Verify that snapshot-specific metadata differs (e.g. UUID, timestamp)
        assert snap1.manifest.snapshot_id != snap2.manifest.snapshot_id

    def test_verify_snapshot_tamper_detection(self, clean_conn: sqlite3.Connection) -> None:
        manager = SnapshotManager()
        repo = KnowledgeRepo(clean_conn)
        project_id = str(uuid.uuid4())
        populate_demo_project(clean_conn, project_id)

        snapshot = manager.create_snapshot(repo, project_id)
        assert manager.verify_snapshot(snapshot) is True

        # Mutate the story (tamper with data)
        mutated_story = dict(snapshot.story)
        mutated_story["idea_text"] = "A modified idea text."
        tampered_snapshot = replace(snapshot, story=mutated_story)

        # Verification must catch this mutation and return False
        assert manager.verify_snapshot(tampered_snapshot) is False

    def test_snapshot_diff(self, clean_conn: sqlite3.Connection) -> None:
        manager = SnapshotManager()
        repo = KnowledgeRepo(clean_conn)
        project_id = str(uuid.uuid4())
        populate_demo_project(clean_conn, project_id)

        snap1 = manager.create_snapshot(repo, project_id)

        # 1. Update story screenplay
        clean_conn.execute(
            "UPDATE story SET screenplay = ? WHERE id = ?", ("SCENE 1: Space. EXT. METEOR - DAY...", project_id)
        )

        # 2. Add compiler metrics
        metric_id = str(uuid.uuid4())
        clean_conn.execute(
            "INSERT INTO compiler_metrics (id, story_id, compiler, metrics_json) "
            "VALUES (?, ?, ?, ?)",
            (metric_id, project_id, "audio", '{"tokens": 100, "time_s": 0.5}'),
        )

        # 3. Add review
        review_id = str(uuid.uuid4())
        clean_conn.execute(
            "INSERT INTO review_log (id, story_id, stage, verdict, comment) "
            "VALUES (?, ?, ?, ?, ?)",
            (review_id, project_id, "audio", "approved", "Perfect speech synthesis."),
        )

        # 4. Modify existing asset's path
        asset_rows = clean_conn.execute("SELECT id FROM assets WHERE story_id = ?", (project_id,)).fetchall()
        asset_id_to_mod = asset_rows[0]["id"]
        clean_conn.execute(
            "UPDATE assets SET file_path = ? WHERE id = ?", ("projects/modified_audio.wav", asset_id_to_mod)
        )
        clean_conn.commit()

        snap2 = manager.create_snapshot(repo, project_id)

        diff = manager.diff_snapshots(snap1, snap2)

        assert diff["project_ids_match"] is True

        # Assert story difference detected
        assert "screenplay" in diff["story"]["modified_fields"]
        old_val, new_val = diff["story"]["modified_fields"]["screenplay"]
        assert old_val == "SCENE 1: Space..."
        assert new_val == "SCENE 1: Space. EXT. METEOR - DAY..."

        # Assert added metrics detected
        added_metrics = diff["compiler_metrics"]["added"]
        assert len(added_metrics) == 1
        assert added_metrics[0]["id"] == metric_id
        assert added_metrics[0]["compiler"] == "audio"

        # Assert added review detected
        added_reviews = diff["review_log"]["added"]
        assert len(added_reviews) == 1
        assert added_reviews[0]["id"] == review_id
        assert added_reviews[0]["stage"] == "audio"

        # Assert modified asset detected
        mod_assets = diff["assets"]["modified"]
        assert len(mod_assets) == 1
        assert mod_assets[0]["id"] == asset_id_to_mod
        assert "file_path" in mod_assets[0]["changes"]
        assert mod_assets[0]["changes"]["file_path"] == ("projects/audio.wav", "projects/modified_audio.wav")

    def test_snapshot_validation_failures(self, clean_conn: sqlite3.Connection) -> None:
        manager = SnapshotManager()
        repo = KnowledgeRepo(clean_conn)
        project_id = str(uuid.uuid4())
        populate_demo_project(clean_conn, project_id)

        snapshot = manager.create_snapshot(repo, project_id)
        assert manager.validate_snapshot(snapshot) == []

        # 1. Invalid manifest UUIDs
        bad_manifest = replace(snapshot.manifest, project_id="not-a-uuid")
        bad_snap = replace(snapshot, manifest=bad_manifest)
        violations = manager.validate_snapshot(bad_snap)
        assert any("project_id 'not-a-uuid' is not a valid UUID" in v for v in violations)

        bad_manifest2 = replace(snapshot.manifest, snapshot_id="not-a-uuid")
        bad_snap2 = replace(snapshot, manifest=bad_manifest2)
        violations2 = manager.validate_snapshot(bad_snap2)
        assert any("snapshot_id 'not-a-uuid' is not a valid UUID" in v for v in violations2)

        # 2. Empty component hashes
        bad_manifest3 = replace(snapshot.manifest, component_hashes={})
        bad_snap3 = replace(snapshot, manifest=bad_manifest3)
        violations3 = manager.validate_snapshot(bad_snap3)
        assert any("component_hashes dictionary is empty or missing" in v for v in violations3)

        # 3. Invalid story created_at format
        bad_story = dict(snapshot.story)
        bad_story["created_at"] = "invalid-date-format"
        bad_snap4 = replace(snapshot, story=bad_story)
        violations4 = manager.validate_snapshot(bad_snap4)
        assert any("created_at 'invalid-date-format' is not a valid ISO 8601 string" in v for v in violations4)

        # 4. Mismatched compiler metrics story_id
        bad_metrics = [dict(m) for m in snapshot.compiler_metrics]
        bad_metrics[0]["story_id"] = str(uuid.uuid4())
        bad_snap5 = replace(snapshot, compiler_metrics=bad_metrics)
        violations5 = manager.validate_snapshot(bad_snap5)
        assert any("compiler_metrics[0] story_id does not match project_id" in v for v in violations5)

        # 5. Invalid review verdict
        bad_reviews = [dict(r) for r in snapshot.review_log]
        bad_reviews[0]["verdict"] = "super-approved"
        bad_snap6 = replace(snapshot, review_log=bad_reviews)
        violations6 = manager.validate_snapshot(bad_snap6)
        assert any("review_log[0] has invalid verdict: 'super-approved'" in v for v in violations6)

        # 6. Invalid asset content_hash length
        bad_assets = [dict(a) for a in snapshot.assets]
        bad_assets[0]["content_hash"] = "short-hash"
        bad_snap7 = replace(snapshot, assets=bad_assets)
        violations7 = manager.validate_snapshot(bad_snap7)
        assert any("content_hash must be a valid 64-character SHA-256 hash" in v for v in violations7)

    def test_performance_check(self, clean_conn: sqlite3.Connection) -> None:
        manager = SnapshotManager()
        repo = KnowledgeRepo(clean_conn)
        project_id = str(uuid.uuid4())

        # Populate with 1 story, 10 compiler metrics, 10 reviews, and 50 assets
        created_at = datetime.now(timezone.utc).isoformat()
        clean_conn.execute(
            "INSERT INTO story (id, idea_text, created_at) VALUES (?, ?, ?)",
            (project_id, "Perf test story.", created_at),
        )
        for i in range(10):
            clean_conn.execute(
                "INSERT INTO compiler_metrics (id, story_id, compiler, metrics_json) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), project_id, f"compiler_{i}", '{"val": 1}'),
            )
            clean_conn.execute(
                "INSERT INTO review_log (id, story_id, stage, verdict) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), project_id, f"stage_{i}", "approved"),
            )
        for i in range(50):
            clean_conn.execute(
                "INSERT INTO assets (id, story_id, capability, file_path, content_hash) VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), project_id, f"cap_{i}", f"path/to/{i}", "c" * 64),
            )
        clean_conn.commit()

        # Measure snapshot creation
        start_time = time.perf_counter()
        snapshot = manager.create_snapshot(repo, project_id)
        creation_duration = (time.perf_counter() - start_time) * 1000

        # Assert creation runs within a performant constraint (< 25ms)
        assert creation_duration < 25.0, f"Snapshot creation was slow: {creation_duration:.2f}ms"

        # Measure snapshot validation
        start_time = time.perf_counter()
        violations = manager.validate_snapshot(snapshot)
        validation_duration = (time.perf_counter() - start_time) * 1000

        assert len(violations) == 0
        assert validation_duration < 15.0, f"Snapshot validation was slow: {validation_duration:.2f}ms"

        # Measure snapshot verification
        start_time = time.perf_counter()
        verified = manager.verify_snapshot(snapshot)
        verification_duration = (time.perf_counter() - start_time) * 1000

        assert verified is True
        assert verification_duration < 15.0, f"Snapshot verification was slow: {verification_duration:.2f}ms"
