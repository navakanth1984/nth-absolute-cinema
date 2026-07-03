from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.portability.export import export_project


def test_export_project_writes_production_package_layout(tmp_path):
    audio_src = tmp_path / "source_audio.wav"
    audio_src.write_bytes(b"RIFF....")

    story = {
        "id": "abc-123",
        "idea_text": "A forgotten temple beneath the sea",
        "story_bible": "# Story Bible\n\nA sunken temple.",
        "screenplay": "INT. TEMPLE - DAY\n\nWater drips.",
        "audio_path": str(audio_src),
        "motion_poster_prompt": "Bioluminescent ruins, cinematic, 16:9",
        "target_runtime_minutes": 15,
    }
    compiler_metrics = [
        {"compiler": "story_compiler", "output_hash": "abc"},
        {"compiler": "screenplay_compiler", "output_hash": "def"},
    ]

    out_dir = tmp_path / "MyMovie"
    result_dir = export_project(story, compiler_metrics, out_dir)

    assert result_dir == out_dir
    assert (out_dir / "story.md").read_text() == story["idea_text"]
    assert (out_dir / "story_bible.md").read_text() == story["story_bible"]
    assert (out_dir / "screenplay.md").read_text() == story["screenplay"]
    assert (out_dir / "screenplay_audio.wav").read_bytes() == b"RIFF...."
    assert (out_dir / "prompts" / "motion_poster.md").read_text() == story["motion_poster_prompt"]

    manifest = json.loads((out_dir / "metadata" / "manifest.json").read_text())
    assert manifest["story_id"] == "abc-123"
    assert manifest["graph_spec_version"] == "1.0"
    assert manifest["compilers_run"] == ["story_compiler", "screenplay_compiler"]

    prov1 = json.loads((out_dir / "provenance" / "story_compiler.json").read_text())
    assert prov1["output_hash"] == "abc"
