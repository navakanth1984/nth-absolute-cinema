from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nac import Studio, SDK_VERSION


def _studio(tmp_path, monkeypatch):
    monkeypatch.setenv("NAC_ROOT_OVERRIDE", str(tmp_path))
    (tmp_path / ".nac-root").write_text("")
    return Studio(provider_override="mock")


def test_sdk_version_is_exported():
    assert SDK_VERSION == "0.1.0"


def test_get_status_tracks_partial_compilation(tmp_path, monkeypatch):
    studio = _studio(tmp_path, monkeypatch)
    pid = studio.create_project("An idea")

    status = studio.get_status(pid)
    assert status["story_bible"] is False

    studio.generate_story(pid)
    status = studio.get_status(pid)
    assert status["story_bible"] is True
    assert status["screenplay"] is False


def test_regenerate_stage_overwrites_existing_output(tmp_path, monkeypatch):
    studio = _studio(tmp_path, monkeypatch)
    pid = studio.create_project("An idea")
    studio.generate_story(pid)
    first = studio._repo.get_story(pid)["story_bible"]

    second = studio.regenerate_stage(pid, "story")
    assert second  # MockProvider is deterministic per (system,prompt), so first==second is fine
    assert studio._repo.get_story(pid)["story_bible"] == second


def test_regenerate_unknown_stage_raises(tmp_path, monkeypatch):
    studio = _studio(tmp_path, monkeypatch)
    pid = studio.create_project("An idea")
    try:
        studio.regenerate_stage(pid, "nonexistent_stage")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "nonexistent_stage" in str(e)


def test_record_and_get_reviews(tmp_path, monkeypatch):
    studio = _studio(tmp_path, monkeypatch)
    pid = studio.create_project("An idea")
    studio.generate_story(pid)

    studio.record_review(pid, "story", "approved")
    reviews = studio.get_reviews(pid)
    assert len(reviews) == 1
    assert reviews[0]["verdict"] == "approved"


def test_import_asset_hashes_and_records(tmp_path, monkeypatch):
    studio = _studio(tmp_path, monkeypatch)
    pid = studio.create_project("An idea")

    fake_poster = tmp_path / "poster.png"
    fake_poster.write_bytes(b"fake-png-bytes")

    asset_id = studio.import_asset(pid, "motion_poster", fake_poster)
    assert asset_id

    assets = studio.get_assets(pid)
    assert len(assets) == 1
    assert assets[0]["capability"] == "motion_poster"

    status = studio.get_status(pid)
    assert status["asset_count"] == 1


def test_import_asset_missing_file_raises(tmp_path, monkeypatch):
    studio = _studio(tmp_path, monkeypatch)
    pid = studio.create_project("An idea")
    try:
        studio.import_asset(pid, "motion_poster", tmp_path / "nonexistent.png")
        assert False, "expected FileNotFoundError"
    except FileNotFoundError:
        pass
