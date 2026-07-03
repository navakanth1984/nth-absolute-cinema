"""nac CLI - the Sprint 1 MVP surface, built entirely on nac.Studio. Never imports
engine.* directly - dogfoods the same SDK boundary agent_os/filmmaking/nac_bridge.py
uses. `py -3 -m cli create "<idea>"` or, once pip-installed, `nac create "<idea>"`.

Checkpoint C.5 adds status/regenerate/review/import-asset: the "minimal local
interface for validating the workflow" - a director can inspect, regenerate one
stage, approve/reject, and import manually-produced assets without a GUI."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nac import Studio, OllamaNotReachableError

def run_pipeline(
    idea_text: str,
    out_dir: Path,
    model: str = "gemma2:9b",
    target_runtime_minutes: int = 15,
    provider_override: str | None = None,
) -> Path:
    studio = Studio(model=model, provider_override=provider_override)

    print(f"[1/6] Creating project for idea: {idea_text!r}")
    project_id = studio.create_project(idea_text, target_runtime_minutes=target_runtime_minutes)

    print("[2/6] Generating Story Bible...")
    studio.generate_story(project_id)

    print("[3/6] Generating Screenplay...")
    studio.generate_screenplay(project_id)

    print("[4/6] Generating Audio Screenplay...")
    studio.generate_audio(project_id)

    print("[5/6] Generating Motion Poster prompt...")
    studio.generate_prompt(project_id)

    print("[6/6] Exporting project...")
    result_dir = studio.export(project_id, out_dir)

    return result_dir


def cmd_status(studio: Studio, project_id: str) -> None:
    status = studio.get_status(project_id)
    print(f"Project {project_id}")
    for key in ("idea", "story_bible", "screenplay", "audio", "motion_poster_prompt"):
        mark = "x" if status[key] else " "
        print(f"  [{mark}] {key}")
    print(f"  assets imported: {status['asset_count']}")
    print(f"  reviews recorded: {status['review_count']}")


def cmd_regenerate(studio: Studio, project_id: str, stage: str) -> None:
    print(f"Regenerating stage '{stage}' for project {project_id}...")
    studio.regenerate_stage(project_id, stage)
    print("Done.")


def cmd_review(studio: Studio, project_id: str) -> None:
    content_by_stage = studio.get_stage_content(project_id)
    for stage, content in content_by_stage.items():
        if not content:
            print(f"\n=== {stage} (not yet generated - skipping) ===")
            continue
        print(f"\n=== {stage} ===")
        print(content[:600] + ("..." if len(content) > 600 else ""))
        verdict = input(f"Verdict for '{stage}' [approved/needs_revision/rejected/skip]: ").strip()
        if verdict and verdict != "skip":
            comment = input("Comment (optional): ").strip() or None
            studio.record_review(project_id, stage, verdict, comment=comment)
            print(f"Recorded: {stage} -> {verdict}")


def cmd_import_asset(studio: Studio, project_id: str, capability: str, file_path: str) -> None:
    asset_id = studio.import_asset(project_id, capability, file_path)
    print(f"Imported asset {asset_id} (capability={capability}) from {file_path}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="nac")
    sub = parser.add_subparsers(dest="command", required=True)

    for cmd_name in ("create", "build"):
        p = sub.add_parser(cmd_name, help="Create a project from an idea and run the full pipeline")
        p.add_argument("idea", help="One-line creative idea")
        p.add_argument("--out", default="MyMovie", help="Export directory name")
        p.add_argument("--model", default="gemma2:9b", help="Ollama model name")
        p.add_argument("--runtime", type=int, default=15, help="Target runtime in minutes")
        p.add_argument(
            "--provider",
            choices=["ollama", "openrouter", "mock"],
            default=None,
            help="Force a specific provider instead of auto-detecting",
        )

    status_p = sub.add_parser("status", help="Show which stages are populated for a project")
    status_p.add_argument("project_id")
    status_p.add_argument("--provider", choices=["ollama", "openrouter", "mock"], default=None)

    regen_p = sub.add_parser("regenerate", help="Re-run exactly one stage for a project")
    regen_p.add_argument("project_id")
    regen_p.add_argument("stage", choices=["story", "screenplay", "audio", "prompt"])
    regen_p.add_argument("--model", default="gemma2:9b")
    regen_p.add_argument("--provider", choices=["ollama", "openrouter", "mock"], default=None)

    review_p = sub.add_parser("review", help="Interactively review each populated stage")
    review_p.add_argument("project_id")
    review_p.add_argument("--provider", choices=["ollama", "openrouter", "mock"], default=None)

    import_p = sub.add_parser(
        "import-asset", help="Import a manually-produced asset (e.g. from Google Flow's UI)"
    )
    import_p.add_argument("project_id")
    import_p.add_argument("capability", help="e.g. motion_poster, soundtrack")
    import_p.add_argument("file_path")
    import_p.add_argument("--provider", choices=["ollama", "openrouter", "mock"], default=None)

    args = parser.parse_args()

    try:
        if args.command in ("create", "build"):
            out_dir = Path(args.out).resolve()
            result_dir = run_pipeline(
                args.idea,
                out_dir,
                model=args.model,
                target_runtime_minutes=args.runtime,
                provider_override=args.provider,
            )
            print(f"\nDone. Project exported to: {result_dir}")
        elif args.command == "status":
            cmd_status(Studio(provider_override=args.provider), args.project_id)
        elif args.command == "regenerate":
            cmd_regenerate(
                Studio(model=args.model, provider_override=args.provider),
                args.project_id,
                args.stage,
            )
        elif args.command == "review":
            cmd_review(Studio(provider_override=args.provider), args.project_id)
        elif args.command == "import-asset":
            cmd_import_asset(
                Studio(provider_override=args.provider),
                args.project_id,
                args.capability,
                args.file_path,
            )
    except OllamaNotReachableError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
