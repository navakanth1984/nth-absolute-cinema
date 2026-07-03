"""nac CLI - the Sprint 1 MVP surface, built entirely on nac.Studio. Never imports
engine.* directly - dogfoods the same SDK boundary agent_os/filmmaking/nac_bridge.py
uses. `py -3 -m cli create "<idea>"` or, once pip-installed, `nac create "<idea>"`."""
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

    args = parser.parse_args()

    if args.command in ("create", "build"):
        try:
            out_dir = Path(args.out).resolve()
            result_dir = run_pipeline(
                args.idea,
                out_dir,
                model=args.model,
                target_runtime_minutes=args.runtime,
                provider_override=args.provider,
            )
            print(f"\nDone. Project exported to: {result_dir}")
        except OllamaNotReachableError as e:
            print(f"\nERROR: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
