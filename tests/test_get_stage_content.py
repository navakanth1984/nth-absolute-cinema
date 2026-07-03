from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nac import Studio


def test_get_stage_content_reflects_generated_stages(tmp_path, monkeypatch):
    monkeypatch.setenv("NAC_ROOT_OVERRIDE", str(tmp_path))
    (tmp_path / ".nac-root").write_text("")

    studio = Studio(provider_override="mock")
    pid = studio.create_project("An idea")

    content = studio.get_stage_content(pid)
    assert content["story"] is None
    assert content["screenplay"] is None

    studio.generate_story(pid)
    content = studio.get_stage_content(pid)
    assert content["story"] is not None
    assert content["screenplay"] is None
