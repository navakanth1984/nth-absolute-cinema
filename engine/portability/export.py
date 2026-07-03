"""Production Package export - a deliberate MVP subset of the full .nac package
format (NAC_PACKAGE_SPEC.md v1.0). No zip, no embedded genomes/graphs, no asset
content-hash dedup - just enough structure (prompts/, provenance/, metadata/) for a
person to open the folder, use what NAC produced, and see how each artifact was made.
Full .nac export/import (manifest schema, asset embed/reference toggle) is Sprint 6
per the original design doc's sprint plan."""
from __future__ import annotations

import json
import shutil
from pathlib import Path


def export_project(story: dict, compiler_metrics: list[dict], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "prompts").mkdir(exist_ok=True)
    (out_dir / "metadata").mkdir(exist_ok=True)
    (out_dir / "provenance").mkdir(exist_ok=True)

    (out_dir / "story.md").write_text(story["idea_text"], encoding="utf-8")
    (out_dir / "story_bible.md").write_text(story["story_bible"] or "", encoding="utf-8")
    (out_dir / "screenplay.md").write_text(story["screenplay"] or "", encoding="utf-8")
    (out_dir / "prompts" / "motion_poster.md").write_text(
        story["motion_poster_prompt"] or "", encoding="utf-8"
    )

    if story.get("audio_path"):
        shutil.copyfile(story["audio_path"], out_dir / "screenplay_audio.wav")

    for m in compiler_metrics:
        (out_dir / "provenance" / f"{m['compiler']}.json").write_text(
            json.dumps(m, indent=2), encoding="utf-8"
        )

    manifest = {
        "story_id": story["id"],
        "graph_spec_version": "1.0",
        "nac_format_version": "0.1.0-mvp",
        "target_runtime_minutes": story["target_runtime_minutes"],
        "compilers_run": [m["compiler"] for m in compiler_metrics],
    }
    (out_dir / "metadata" / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    return out_dir
