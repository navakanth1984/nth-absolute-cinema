"""Serializer and Deserializer for uncompressed .nac directory packages."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from engine.portability.snapshot import Snapshot, SnapshotManifest, SnapshotManager


class NacSerializer:
    """Serializes a Snapshot object into a deterministic, uncompressed .nac directory package."""

    @staticmethod
    def _write_deterministic_json(path: Path, data: Any) -> None:
        """Write JSON data with sorted keys and consistent spacing to guarantee byte-for-byte determinism."""
        path.parent.mkdir(parents=True, exist_ok=True)
        # Using sorted keys and indent=2 to ensure deterministic file contents
        content = json.dumps(data, sort_keys=True, indent=2, default=str)
        path.write_text(content, encoding="utf-8")

    def serialize(self, snapshot: Snapshot, target_dir: Path | str) -> Path:
        """Serialize the Snapshot into an uncompressed .nac directory layout."""
        target_path = Path(target_dir).resolve()
        target_path.mkdir(parents=True, exist_ok=True)

        # 1. Serialize manifest.json at root
        manifest_data = {
            "project_id": snapshot.manifest.project_id,
            "snapshot_id": snapshot.manifest.snapshot_id,
            "data_hash": snapshot.manifest.data_hash,
            "component_hashes": snapshot.manifest.component_hashes,
            "engine_version": snapshot.manifest.engine_version,
            "sdk_version": snapshot.manifest.sdk_version,
            "graph_spec_version": snapshot.manifest.graph_spec_version,
            "genome_spec_version": snapshot.manifest.genome_spec_version,
            "created_at": snapshot.manifest.created_at,
            "compiler_versions": snapshot.manifest.compiler_versions,
            "pack_versions": snapshot.manifest.pack_versions,
            "provider_metadata": snapshot.manifest.provider_metadata,
            "environment_metadata": snapshot.manifest.environment_metadata,
            "runtime_config": snapshot.manifest.runtime_config,
        }
        self._write_deterministic_json(target_path / "manifest.json", manifest_data)

        # 2. Serialize graphs/
        self._write_deterministic_json(
            target_path / "graphs" / "knowledge_graph.json",
            snapshot.story,
        )
        self._write_deterministic_json(
            target_path / "graphs" / "cinematic_graph.json",
            {},  # minimal empty representation matching specs
        )
        self._write_deterministic_json(
            target_path / "graphs" / "asset_graph.json",
            {"assets": sorted(snapshot.assets, key=lambda x: x.get("id", ""))},
        )
        self._write_deterministic_json(
            target_path / "graphs" / "production_graph.json",
            {"compiler_metrics": sorted(snapshot.compiler_metrics, key=lambda x: x.get("id", ""))},
        )
        self._write_deterministic_json(
            target_path / "graphs" / "review_graph.json",
            {"review_log": sorted(snapshot.review_log, key=lambda x: x.get("id", ""))},
        )

        # 3. Serialize genomes/
        genomes_dir = target_path / "genomes"
        genomes_dir.mkdir(exist_ok=True)
        # Empty genomes mapping for now (Sprint 2B not started)
        self._write_deterministic_json(genomes_dir / "genomes.json", snapshot.genomes)

        # 4. Serialize assets/ references
        assets_dir = target_path / "assets"
        assets_dir.mkdir(exist_ok=True)
        self._write_deterministic_json(
            assets_dir / "references.json",
            {"references": sorted(snapshot.assets, key=lambda x: x.get("id", ""))},
        )

        # 5. Serialize reviews/
        reviews_dir = target_path / "reviews"
        reviews_dir.mkdir(exist_ok=True)
        self._write_deterministic_json(
            reviews_dir / "review_history.json",
            {"review_log": sorted(snapshot.review_log, key=lambda x: x.get("id", ""))},
        )

        # 6. Serialize provenance/ & metrics/
        provenance_dir = target_path / "provenance"
        provenance_dir.mkdir(exist_ok=True)
        for metric in snapshot.compiler_metrics:
            comp_name = metric.get("compiler", "unknown")
            self._write_deterministic_json(
                provenance_dir / f"{comp_name}_provenance.json",
                metric,
            )

        metrics_dir = target_path / "metrics"
        metrics_dir.mkdir(exist_ok=True)
        self._write_deterministic_json(
            metrics_dir / "compiler_metrics.json",
            {"compiler_metrics": sorted(snapshot.compiler_metrics, key=lambda x: x.get("id", ""))},
        )

        return target_path


class NacDeserializer:
    """Deserializes an uncompressed .nac directory package into a Snapshot object, verifying integrity."""

    @staticmethod
    def _read_json(path: Path) -> Any:
        """Reads JSON data from the specified path."""
        if not path.is_file():
            raise FileNotFoundError(f"Required package file not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def deserialize(self, package_dir: Path | str) -> Snapshot:
        """Deserialize an uncompressed .nac directory layout back into a Snapshot object."""
        package_path = Path(package_dir).resolve()
        if not package_path.is_dir():
            raise FileNotFoundError(f"Package directory does not exist: {package_path}")

        # 1. Read manifest.json
        manifest_data = self._read_json(package_path / "manifest.json")
        manifest = SnapshotManifest(
            project_id=manifest_data["project_id"],
            snapshot_id=manifest_data["snapshot_id"],
            data_hash=manifest_data["data_hash"],
            component_hashes=manifest_data["component_hashes"],
            engine_version=manifest_data.get("engine_version", "0.1.0"),
            sdk_version=manifest_data.get("sdk_version", "0.1.0"),
            graph_spec_version=manifest_data.get("graph_spec_version", "1.2"),
            genome_spec_version=manifest_data.get("genome_spec_version", "1.2"),
            created_at=manifest_data["created_at"],
            compiler_versions=manifest_data.get("compiler_versions", {}),
            pack_versions=manifest_data.get("pack_versions", {}),
            provider_metadata=manifest_data.get("provider_metadata", {}),
            environment_metadata=manifest_data.get("environment_metadata", {}),
            runtime_config=manifest_data.get("runtime_config", {}),
        )

        # 2. Read story (KnowledgeGraph)
        story = self._read_json(package_path / "graphs" / "knowledge_graph.json")

        # 3. Read compiler metrics (ProductionGraph)
        prod_data = self._read_json(package_path / "graphs" / "production_graph.json")
        compiler_metrics = prod_data.get("compiler_metrics", [])

        # 4. Read review log (ReviewGraph)
        review_data = self._read_json(package_path / "graphs" / "review_graph.json")
        review_log = review_data.get("review_log", [])

        # 5. Read assets (AssetGraph)
        asset_data = self._read_json(package_path / "graphs" / "asset_graph.json")
        assets = asset_data.get("assets", [])

        # 6. Read genomes
        genomes = self._read_json(package_path / "genomes" / "genomes.json")

        snapshot = Snapshot(
            manifest=manifest,
            story=story,
            compiler_metrics=compiler_metrics,
            review_log=review_log,
            assets=assets,
            genomes=genomes,
        )

        # 7. Verify integrity using SnapshotManager
        if not SnapshotManager().verify_snapshot(snapshot):
            raise ValueError(
                "Package deserialization failed: Cryptographic integrity check failed (data hash mismatch)."
            )

        return snapshot
