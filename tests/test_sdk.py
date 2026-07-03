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


def test_studio_remaining_unimplemented_stages_raise_named_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("NAC_ROOT_OVERRIDE", str(tmp_path))
    (tmp_path / ".nac-root").write_text("")

    studio = Studio(provider_override="mock")
    project_id = studio.create_project("idea")
    studio.generate_story(project_id)
    studio.generate_screenplay(project_id)

    try:
        studio.generate_audio(project_id)
        assert False, "expected NotImplementedError"
    except NotImplementedError as e:
        assert "Checkpoint C" in str(e)
