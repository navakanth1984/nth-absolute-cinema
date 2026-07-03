from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nac import Studio


def _studio(tmp_path, monkeypatch):
    monkeypatch.setenv("NAC_ROOT_OVERRIDE", str(tmp_path))
    (tmp_path / ".nac-root").write_text("")
    return Studio(provider_override="mock")


def test_list_projects_empty(tmp_path, monkeypatch):
    studio = _studio(tmp_path, monkeypatch)
    assert studio.list_projects() == []


def test_list_projects_single(tmp_path, monkeypatch):
    studio = _studio(tmp_path, monkeypatch)
    pid = studio.create_project("A temple in the clouds", target_runtime_minutes=20)

    projects = studio.list_projects()
    assert len(projects) == 1
    assert projects[0]["id"] == pid
    assert projects[0]["idea_text"] == "A temple in the clouds"
    assert projects[0]["target_runtime_minutes"] == 20
    assert projects[0]["story_bible"] is False


def test_list_projects_reflects_stage_completion(tmp_path, monkeypatch):
    studio = _studio(tmp_path, monkeypatch)
    pid = studio.create_project("An idea")
    studio.generate_story(pid)

    projects = studio.list_projects()
    assert projects[0]["story_bible"] is True
    assert projects[0]["screenplay"] is False


def test_list_projects_multiple_ordered_most_recent_first(tmp_path, monkeypatch):
    studio = _studio(tmp_path, monkeypatch)
    first = studio.create_project("First idea")
    second = studio.create_project("Second idea")
    third = studio.create_project("Third idea")

    ids = [p["id"] for p in studio.list_projects()]
    assert ids[0] == third
    assert set(ids) == {first, second, third}


def test_get_metrics_empty_before_generation(tmp_path, monkeypatch):
    studio = _studio(tmp_path, monkeypatch)
    pid = studio.create_project("An idea")
    assert studio.get_metrics(pid) == []


def test_get_metrics_after_generation(tmp_path, monkeypatch):
    studio = _studio(tmp_path, monkeypatch)
    pid = studio.create_project("An idea")
    studio.generate_story(pid)

    metrics = studio.get_metrics(pid)
    assert len(metrics) == 1
    assert metrics[0]["compiler"]


def test_get_provider_info_reports_mock(tmp_path, monkeypatch):
    studio = _studio(tmp_path, monkeypatch)
    info = studio.get_provider_info()
    assert info["llm_provider"] == "MockProvider"


def test_get_capabilities_matches_registry(tmp_path, monkeypatch):
    studio = _studio(tmp_path, monkeypatch)
    capabilities = studio.get_capabilities()
    names = {c["capability"] for c in capabilities}
    assert "screenplay" in names
    assert "narration" in names
    unavailable = [c for c in capabilities if not c["available"]]
    assert unavailable  # honestly reports at least one not-yet-integrated capability


def test_get_audio_path_none_before_generation(tmp_path, monkeypatch):
    studio = _studio(tmp_path, monkeypatch)
    pid = studio.create_project("An idea")
    assert studio.get_audio_path(pid) is None


def test_create_demo_project_seeds_story_and_screenplay(tmp_path, monkeypatch):
    studio = _studio(tmp_path, monkeypatch)
    pid = studio.create_demo_project()

    status = studio.get_status(pid)
    assert status["story_bible"] is True
    assert status["screenplay"] is True
    assert status["audio"] is False  # left ungenerated - demo shows the workflow, isn't a finished artifact

    content = studio.get_stage_content(pid)
    assert "Temple of Varuna" in content["story"]
    assert "AMRITA" in content["screenplay"]

    metrics = studio.get_metrics(pid)
    assert metrics == []  # seeded directly, not via a compiler - no metrics recorded, honestly


def test_demo_project_appears_in_list_projects(tmp_path, monkeypatch):
    studio = _studio(tmp_path, monkeypatch)
    pid = studio.create_demo_project()

    projects = studio.list_projects()
    assert any(p["id"] == pid for p in projects)
