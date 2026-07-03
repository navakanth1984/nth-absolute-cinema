from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nac import Studio


def test_studio_create_project_returns_id(tmp_path, monkeypatch):
    monkeypatch.setenv("NAC_ROOT_OVERRIDE", str(tmp_path))
    (tmp_path / ".nac-root").write_text("")

    studio = Studio(provider_override="mock")
    project_id = studio.create_project("A forgotten temple beneath the sea")

    assert project_id


def test_studio_generate_story_and_screenplay_work_offline_with_mock(tmp_path, monkeypatch):
    monkeypatch.setenv("NAC_ROOT_OVERRIDE", str(tmp_path))
    (tmp_path / ".nac-root").write_text("")

    studio = Studio(provider_override="mock")
    project_id = studio.create_project("A forgotten temple beneath the sea")

    bible = studio.generate_story(project_id)
    assert "MOCK OUTPUT" in bible

    screenplay = studio.generate_screenplay(project_id)
    assert "MOCK OUTPUT" in screenplay


def test_studio_full_pipeline_offline_with_mock(tmp_path, monkeypatch):
    monkeypatch.setenv("NAC_ROOT_OVERRIDE", str(tmp_path))
    (tmp_path / ".nac-root").write_text("")

    studio = Studio(provider_override="mock")
    project_id = studio.create_project("A forgotten temple beneath the sea")

    studio.generate_story(project_id)
    studio.generate_screenplay(project_id)
    audio_path = studio.generate_audio(project_id)
    prompt = studio.generate_prompt(project_id)

    assert audio_path.exists()
    assert "16:9" in prompt

    out_dir = tmp_path / "MyMovie"
    result_dir = studio.export(project_id, out_dir)

    assert (result_dir / "story.md").exists()
    assert (result_dir / "story_bible.md").exists()
    assert (result_dir / "screenplay.md").exists()
    assert (result_dir / "screenplay_audio.wav").exists()
    assert (result_dir / "prompts" / "motion_poster.md").exists()
    assert (result_dir / "metadata" / "manifest.json").exists()
    assert (result_dir / "provenance" / "story_compiler.json").exists()
    assert (result_dir / "provenance" / "screenplay_compiler.json").exists()
    assert (result_dir / "provenance" / "audio_compiler.json").exists()
    assert (result_dir / "provenance" / "prompt_compiler.json").exists()
