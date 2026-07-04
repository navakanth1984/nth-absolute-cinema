"""Immutable Snapshot model and SnapshotManager for managing NAC project state."""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import sqlite3


@dataclass(frozen=True)
class SnapshotManifest:
    """Metadata describing a snapshot."""
    project_id: str
    snapshot_id: str
    data_hash: str
    snapshot_schema_version: str = "1.0"
    graph_spec_version: str = "1.2"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    compiler_versions: dict[str, str] = field(default_factory=dict)
    pack_versions: dict[str, str] = field(default_factory=dict)
    runtime_config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Snapshot:
    """An immutable container representing the complete creative state of a project."""
    manifest: SnapshotManifest
    story: dict[str, Any]
    compiler_metrics: list[dict[str, Any]]
    review_log: list[dict[str, Any]]
    assets: list[dict[str, Any]]
    genomes: dict[str, Any] = field(default_factory=dict)
    custom_metadata: dict[str, Any] = field(default_factory=dict)


class SnapshotManager:
    """Manages the creation, validation, verification, diffing, and restoration of Snapshots."""

    @staticmethod
    def _compute_data_hash(
        story: dict[str, Any],
        compiler_metrics: list[dict[str, Any]],
        review_log: list[dict[str, Any]],
        assets: list[dict[str, Any]],
        genomes: dict[str, Any]
    ) -> str:
        """Deterministically hashes the core data of the snapshot to guarantee integrity."""
        # Sort lists of dicts by their unique IDs (or all items) for determinism
        metrics_sorted = sorted(compiler_metrics, key=lambda x: x.get("id", ""))
        reviews_sorted = sorted(review_log, key=lambda x: x.get("id", ""))
        assets_sorted = sorted(assets, key=lambda x: x.get("id", ""))

        data_to_hash = {
            "story": story,
            "compiler_metrics": metrics_sorted,
            "review_log": reviews_sorted,
            "assets": assets_sorted,
            "genomes": genomes,
        }

        # Deterministic serialization: sorted keys, string representation for non-JSON objects
        serialized = json.dumps(data_to_hash, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def create_snapshot(
        self,
        conn: sqlite3.Connection,
        project_id: str,
        compiler_versions: dict[str, str] | None = None,
        pack_versions: dict[str, str] | None = None,
        runtime_config: dict[str, Any] | None = None
    ) -> Snapshot:
        """Query the SQLite database for a project's tables and construct a Snapshot."""
        # 1. Fetch story record
        story_row = conn.execute(
            "SELECT * FROM story WHERE id = ?", (project_id,)
        ).fetchone()
        if story_row is None:
            raise KeyError(f"Project story '{project_id}' not found in database.")
        story = dict(story_row)

        # 2. Fetch compiler metrics
        metrics_rows = conn.execute(
            "SELECT * FROM compiler_metrics WHERE story_id = ?", (project_id,)
        ).fetchall()
        compiler_metrics = [dict(r) for r in metrics_rows]

        # 3. Fetch reviews
        review_rows = conn.execute(
            "SELECT * FROM review_log WHERE story_id = ?", (project_id,)
        ).fetchall()
        review_log = [dict(r) for r in review_rows]

        # 4. Fetch assets
        asset_rows = conn.execute(
            "SELECT * FROM assets WHERE story_id = ?", (project_id,)
        ).fetchall()
        assets = [dict(r) for r in asset_rows]

        # Genomes are currently not stored in separate tables ( Sprint 2B is not started).
        # We model them as an empty dict structure for spec completeness.
        genomes: dict[str, Any] = {}

        # 5. Compute deterministic data hash
        data_hash = self._compute_data_hash(story, compiler_metrics, review_log, assets, genomes)

        # 6. Build Manifest
        manifest = SnapshotManifest(
            project_id=project_id,
            snapshot_id=str(uuid.uuid4()),
            data_hash=data_hash,
            compiler_versions=compiler_versions or {},
            pack_versions=pack_versions or {},
            runtime_config=runtime_config or {},
        )

        return Snapshot(
            manifest=manifest,
            story=story,
            compiler_metrics=compiler_metrics,
            review_log=review_log,
            assets=assets,
            genomes=genomes,
        )

    def validate_snapshot(self, snapshot: Snapshot) -> list[str]:
        """Perform structural validation on the snapshot schemas and relationships.
        Returns a list of violation error strings (empty list indicates a valid snapshot).
        """
        violations: list[str] = []

        # 1. Validate manifest IDs
        try:
            uuid.UUID(snapshot.manifest.project_id)
        except ValueError:
            violations.append(f"Manifest project_id '{snapshot.manifest.project_id}' is not a valid UUID.")

        try:
            uuid.UUID(snapshot.manifest.snapshot_id)
        except ValueError:
            violations.append(f"Manifest snapshot_id '{snapshot.manifest.snapshot_id}' is not a valid UUID.")

        # 2. Validate story node
        story = snapshot.story
        if "id" not in story or story["id"] != snapshot.manifest.project_id:
            violations.append("Story id is missing or does not match manifest project_id.")
        if "idea_text" not in story or not story["idea_text"].strip():
            violations.append("Story idea_text is missing or empty.")
        if "created_at" in story:
            try:
                datetime.fromisoformat(story["created_at"])
            except ValueError:
                violations.append(f"Story created_at '{story['created_at']}' is not a valid ISO 8601 string.")

        # 3. Validate metrics rows
        for idx, m in enumerate(snapshot.compiler_metrics):
            if m.get("story_id") != snapshot.manifest.project_id:
                violations.append(f"compiler_metrics[{idx}] story_id does not match project_id.")
            if not m.get("id"):
                violations.append(f"compiler_metrics[{idx}] is missing an id.")
            if not m.get("compiler"):
                violations.append(f"compiler_metrics[{idx}] is missing compiler name.")

        # 4. Validate reviews
        for idx, r in enumerate(snapshot.review_log):
            if r.get("story_id") != snapshot.manifest.project_id:
                violations.append(f"review_log[{idx}] story_id does not match project_id.")
            if not r.get("id"):
                violations.append(f"review_log[{idx}] is missing an id.")
            if not r.get("stage"):
                violations.append(f"review_log[{idx}] is missing a stage.")
            if r.get("verdict") not in ["approved", "rejected", "needs_revision"]:
                violations.append(f"review_log[{idx}] has invalid verdict: '{r.get('verdict')}'")

        # 5. Validate assets
        for idx, a in enumerate(snapshot.assets):
            if a.get("story_id") != snapshot.manifest.project_id:
                violations.append(f"assets[{idx}] story_id does not match project_id.")
            if not a.get("id"):
                violations.append(f"assets[{idx}] is missing an id.")
            if not a.get("file_path"):
                violations.append(f"assets[{idx}] is missing a file_path.")
            if not a.get("content_hash") or len(a.get("content_hash")) != 64:
                violations.append(f"assets[{idx}] content_hash must be a valid 64-character SHA-256 hash.")

        return violations

    def verify_snapshot(self, snapshot: Snapshot) -> bool:
        """Cryptographically verifies data integrity of the snapshot against its manifest hash."""
        recomputed_hash = self._compute_data_hash(
            snapshot.story,
            snapshot.compiler_metrics,
            snapshot.review_log,
            snapshot.assets,
            snapshot.genomes,
        )
        return recomputed_hash == snapshot.manifest.data_hash

    def diff_snapshots(self, snap1: Snapshot, snap2: Snapshot) -> dict[str, Any]:
        """Produce a detailed, structured diff comparing two snapshots.
        Optimized for tracking history, change resolution, and debugging non-determinism.
        """
        story_diff: dict[str, tuple[Any, Any]] = {}
        s1 = snap1.story
        s2 = snap2.story

        # Diff story fields
        all_story_keys = set(s1.keys()).union(s2.keys())
        for k in all_story_keys:
            if s1.get(k) != s2.get(k):
                story_diff[k] = (s1.get(k), s2.get(k))

        # Diff compiler metrics lists
        m1_map = {m["id"]: m for m in snap1.compiler_metrics if "id" in m}
        m2_map = {m["id"]: m for m in snap2.compiler_metrics if "id" in m}

        added_metrics = [m2_map[mid] for mid in m2_map if mid not in m1_map]
        removed_metrics = [m1_map[mid] for mid in m1_map if mid not in m2_map]
        modified_metrics: list[dict[str, Any]] = []

        for mid in set(m1_map.keys()).intersection(m2_map.keys()):
            metric_diff = {}
            for k in set(m1_map[mid].keys()).union(m2_map[mid].keys()):
                if m1_map[mid].get(k) != m2_map[mid].get(k):
                    metric_diff[k] = (m1_map[mid].get(k), m2_map[mid].get(k))
            if metric_diff:
                modified_metrics.append({"id": mid, "compiler": m1_map[mid].get("compiler"), "changes": metric_diff})

        # Diff reviews lists
        r1_map = {r["id"]: r for r in snap1.review_log if "id" in r}
        r2_map = {r["id"]: r for r in snap2.review_log if "id" in r}

        added_reviews = [r2_map[rid] for rid in r2_map if rid not in r1_map]
        removed_reviews = [r1_map[rid] for rid in r1_map if rid not in r2_map]

        # Diff assets lists
        a1_map = {a["id"]: a for a in snap1.assets if "id" in a}
        a2_map = {a["id"]: a for a in snap2.assets if "id" in a}

        added_assets = [a2_map[aid] for aid in a2_map if aid not in a1_map]
        removed_assets = [a1_map[aid] for aid in a1_map if aid not in a2_map]
        modified_assets: list[dict[str, Any]] = []

        for aid in set(a1_map.keys()).intersection(a2_map.keys()):
            asset_diff = {}
            for k in set(a1_map[aid].keys()).union(a2_map[aid].keys()):
                if a1_map[aid].get(k) != a2_map[aid].get(k):
                    asset_diff[k] = (a1_map[aid].get(k), a2_map[aid].get(k))
            if asset_diff:
                modified_assets.append({"id": aid, "capability": a1_map[aid].get("capability"), "changes": asset_diff})

        return {
            "project_ids_match": snap1.manifest.project_id == snap2.manifest.project_id,
            "story": {
                "modified_fields": story_diff,
            },
            "compiler_metrics": {
                "added": added_metrics,
                "removed": removed_metrics,
                "modified": modified_metrics,
            },
            "review_log": {
                "added": added_reviews,
                "removed": removed_reviews,
            },
            "assets": {
                "added": added_assets,
                "removed": removed_assets,
                "modified": modified_assets,
            },
        }

    def restore_in_memory(self, snapshot: Snapshot, conn: sqlite3.Connection) -> None:
        """Restores the snapshot data back into SQLite tables of the specified connection.
        Performs an overwrite restore by clearing prior data associated with the project_id.
        """
        project_id = snapshot.manifest.project_id

        # Verify integrity before starting restore
        if not self.verify_snapshot(snapshot):
            raise ValueError("Cannot restore snapshot: integrity verification check failed (data hash mismatch).")

        # 1. Clear existing data
        conn.execute("DELETE FROM assets WHERE story_id = ?", (project_id,))
        conn.execute("DELETE FROM review_log WHERE story_id = ?", (project_id,))
        conn.execute("DELETE FROM compiler_metrics WHERE story_id = ?", (project_id,))
        conn.execute("DELETE FROM story WHERE id = ?", (project_id,))

        # 2. Insert story
        s = snapshot.story
        conn.execute(
            "INSERT INTO story (id, idea_text, target_runtime_minutes, story_bible, screenplay, audio_path, motion_poster_prompt, graph_spec_version, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                s["id"],
                s["idea_text"],
                s["target_runtime_minutes"],
                s.get("story_bible"),
                s.get("screenplay"),
                s.get("audio_path"),
                s.get("motion_poster_prompt"),
                s.get("graph_spec_version", "1.0"),
                s["created_at"],
            ),
        )

        # 3. Insert compiler metrics
        for m in snapshot.compiler_metrics:
            conn.execute(
                "INSERT INTO compiler_metrics (id, story_id, compiler, metrics_json, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (m["id"], m["story_id"], m["compiler"], m["metrics_json"], m["created_at"]),
            )

        # 4. Insert review log
        for r in snapshot.review_log:
            conn.execute(
                "INSERT INTO review_log (id, story_id, stage, verdict, comment, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (r["id"], r["story_id"], r["stage"], r["verdict"], r.get("comment"), r["created_at"]),
            )

        # 5. Insert assets
        for a in snapshot.assets:
            conn.execute(
                "INSERT INTO assets (id, story_id, capability, file_path, content_hash, source, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (a["id"], a["story_id"], a["capability"], a["file_path"], a["content_hash"], a.get("source", "manual_import"), a["created_at"]),
            )

        conn.commit()
