import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from engine.storage.knowledge_repo import KnowledgeRepo
from engine.portability.snapshot import Snapshot, SnapshotManager
from engine.portability.serializer import NacSerializer, NacDeserializer


@pytest.fixture
def clean_conn() -> sqlite3.Connection:
    """Create a clean in-memory SQLite database initialized with the schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from engine.storage.db import SCHEMA
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def populate_test_project(conn: sqlite3.Connection, project_id: str) -> None:
    """Helper to populate a test database with project details."""
    created_at = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO story (id, idea_text, target_runtime_minutes, story_bible, screenplay, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (project_id, "Journey to the outer rim.", 30, "World rules detail...", "SCENE 1: Spaceflight...", created_at),
    )

    # 2 Metrics
    conn.execute(
        "INSERT INTO compiler_metrics (id, story_id, compiler, metrics_json, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), project_id, "story", '{"tokens": 150, "time_s": 0.8}', created_at),
    )
    conn.execute(
        "INSERT INTO compiler_metrics (id, story_id, compiler, metrics_json, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), project_id, "screenplay", '{"tokens": 320, "time_s": 2.1}', created_at),
    )

    # 2 Reviews
    conn.execute(
        "INSERT INTO review_log (id, story_id, stage, verdict, comment, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), project_id, "story", "approved", "Excellent logic.", created_at),
    )
    conn.execute(
        "INSERT INTO review_log (id, story_id, stage, verdict, comment, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), project_id, "screenplay", "approved", "Good dialog.", created_at),
    )

    # 2 Assets
    conn.execute(
        "INSERT INTO assets (id, story_id, capability, file_path, content_hash, source, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), project_id, "audio", "projects/audio.wav", "1" * 64, "compiler", created_at),
    )
    conn.execute(
        "INSERT INTO assets (id, story_id, capability, file_path, content_hash, source, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), project_id, "image", "projects/poster.png", "2" * 64, "manual_import", created_at),
    )
    conn.commit()


def compute_file_hash(path: Path) -> str:
    """Compute the SHA-256 hash of a file's contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestNacSerializerDeserializer:
    """Test suite for NacSerializer and NacDeserializer."""

    def test_serialization_happy_path_layout(self, clean_conn: sqlite3.Connection, tmp_path: Path) -> None:
        project_id = str(uuid.uuid4())
        populate_test_project(clean_conn, project_id)

        repo = KnowledgeRepo(clean_conn)
        snapshot = SnapshotManager().create_snapshot(repo, project_id)

        serializer = NacSerializer()
        package_dir = tmp_path / "test_project.nac"
        serializer.serialize(snapshot, package_dir)

        # Assert uncompressed directory layout files exist
        assert (package_dir / "manifest.json").is_file()
        assert (package_dir / "graphs" / "knowledge_graph.json").is_file()
        assert (package_dir / "graphs" / "cinematic_graph.json").is_file()
        assert (package_dir / "graphs" / "asset_graph.json").is_file()
        assert (package_dir / "graphs" / "production_graph.json").is_file()
        assert (package_dir / "graphs" / "review_graph.json").is_file()
        assert (package_dir / "genomes" / "genomes.json").is_file()
        assert (package_dir / "assets" / "references.json").is_file()
        assert (package_dir / "reviews" / "review_history.json").is_file()
        assert (package_dir / "metrics" / "compiler_metrics.json").is_file()
        assert (package_dir / "provenance" / "story_provenance.json").is_file()
        assert (package_dir / "provenance" / "screenplay_provenance.json").is_file()

        # Check content structure of manifest
        manifest_data = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
        assert manifest_data["project_id"] == project_id
        assert manifest_data["engine_version"] == "0.1.0"
        assert manifest_data["sdk_version"] == "0.1.0"
        assert manifest_data["graph_spec_version"] == "1.2"
        assert manifest_data["genome_spec_version"] == "1.2"
        assert "story" in manifest_data["component_hashes"]

    def test_serialization_determinism(self, clean_conn: sqlite3.Connection, tmp_path: Path) -> None:
        project_id = str(uuid.uuid4())
        populate_test_project(clean_conn, project_id)

        repo = KnowledgeRepo(clean_conn)
        snapshot = SnapshotManager().create_snapshot(repo, project_id)

        serializer = NacSerializer()
        dir1 = tmp_path / "dir1.nac"
        dir2 = tmp_path / "dir2.nac"

        serializer.serialize(snapshot, dir1)
        serializer.serialize(snapshot, dir2)

        # Assert all files inside dir1 are byte-for-byte identical to the ones in dir2
        files1 = sorted([p.relative_to(dir1) for p in dir1.rglob("*") if p.is_file()])
        files2 = sorted([p.relative_to(dir2) for p in dir2.rglob("*") if p.is_file()])

        assert files1 == files2

        for rel_path in files1:
            file1_hash = compute_file_hash(dir1 / rel_path)
            file2_hash = compute_file_hash(dir2 / rel_path)
            assert file1_hash == file2_hash, f"File content mismatch: {rel_path}"

    def test_deserialization_happy_path(self, clean_conn: sqlite3.Connection, tmp_path: Path) -> None:
        project_id = str(uuid.uuid4())
        populate_test_project(clean_conn, project_id)

        repo = KnowledgeRepo(clean_conn)
        original_snapshot = SnapshotManager().create_snapshot(repo, project_id)

        serializer = NacSerializer()
        deserializer = NacDeserializer()
        package_dir = tmp_path / "restore_project.nac"

        serializer.serialize(original_snapshot, package_dir)
        restored_snapshot = deserializer.deserialize(package_dir)

        # Verify restored snapshot fields match original
        assert restored_snapshot.manifest.project_id == original_snapshot.manifest.project_id
        assert restored_snapshot.manifest.snapshot_id == original_snapshot.manifest.snapshot_id
        assert restored_snapshot.manifest.data_hash == original_snapshot.manifest.data_hash
        assert restored_snapshot.manifest.component_hashes == original_snapshot.manifest.component_hashes
        assert restored_snapshot.story["idea_text"] == original_snapshot.story["idea_text"]
        assert len(restored_snapshot.compiler_metrics) == len(original_snapshot.compiler_metrics)
        assert len(restored_snapshot.review_log) == len(original_snapshot.review_log)
        assert len(restored_snapshot.assets) == len(original_snapshot.assets)

    def test_deserialization_integrity_mismatch_raises_value_error(self, clean_conn: sqlite3.Connection, tmp_path: Path) -> None:
        project_id = str(uuid.uuid4())
        populate_test_project(clean_conn, project_id)

        repo = KnowledgeRepo(clean_conn)
        original_snapshot = SnapshotManager().create_snapshot(repo, project_id)

        serializer = NacSerializer()
        deserializer = NacDeserializer()
        package_dir = tmp_path / "tamper_project.nac"

        serializer.serialize(original_snapshot, package_dir)

        # Tamper with the serialized graphs/knowledge_graph.json
        kg_path = package_dir / "graphs" / "knowledge_graph.json"
        kg_data = json.loads(kg_path.read_text(encoding="utf-8"))
        kg_data["idea_text"] = "A modified untracked idea."
        kg_path.write_text(json.dumps(kg_data), encoding="utf-8")

        # Deserializing should raise a ValueError due to hash mismatch
        with pytest.raises(ValueError) as exc:
            deserializer.deserialize(package_dir)
        assert "integrity check failed" in str(exc.value)

    def test_deserialization_missing_file_raises_error(self, clean_conn: sqlite3.Connection, tmp_path: Path) -> None:
        project_id = str(uuid.uuid4())
        populate_test_project(clean_conn, project_id)

        repo = KnowledgeRepo(clean_conn)
        original_snapshot = SnapshotManager().create_snapshot(repo, project_id)

        serializer = NacSerializer()
        deserializer = NacDeserializer()
        package_dir = tmp_path / "missing_file_project.nac"

        serializer.serialize(original_snapshot, package_dir)

        # Remove manifest.json
        (package_dir / "manifest.json").unlink()

        with pytest.raises(FileNotFoundError):
            deserializer.deserialize(package_dir)

        # Re-serialize and delete knowledge_graph.json
        serializer.serialize(original_snapshot, package_dir)
        (package_dir / "graphs" / "knowledge_graph.json").unlink()

        with pytest.raises(FileNotFoundError):
            deserializer.deserialize(package_dir)
