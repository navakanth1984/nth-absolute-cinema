from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.storage.db import init_db
from engine.storage.knowledge_repo import KnowledgeRepo


def _repo(tmp_path):
    conn = init_db(tmp_path / "test.db")
    return KnowledgeRepo(conn)


def test_get_status_reflects_populated_fields(tmp_path):
    repo = _repo(tmp_path)
    story_id = repo.create_story("An idea")

    status = repo.get_status(story_id)
    assert status["idea"] is True
    assert status["story_bible"] is False
    assert status["screenplay"] is False
    assert status["asset_count"] == 0
    assert status["review_count"] == 0

    repo.save_story_bible(story_id, "# Bible")
    status = repo.get_status(story_id)
    assert status["story_bible"] is True
    assert status["screenplay"] is False


def test_record_and_get_reviews(tmp_path):
    repo = _repo(tmp_path)
    story_id = repo.create_story("An idea")

    repo.record_review(story_id, "story_bible", "approved")
    repo.record_review(story_id, "screenplay", "needs_revision", comment="pacing too slow")

    reviews = repo.get_reviews(story_id)
    assert len(reviews) == 2
    assert reviews[0]["stage"] == "story_bible"
    assert reviews[0]["verdict"] == "approved"
    assert reviews[1]["comment"] == "pacing too slow"

    status = repo.get_status(story_id)
    assert status["review_count"] == 2


def test_import_and_get_assets(tmp_path):
    repo = _repo(tmp_path)
    story_id = repo.create_story("An idea")

    asset_id = repo.import_asset(story_id, "motion_poster", "/path/to/poster.png", "abc123hash")
    assert asset_id

    assets = repo.get_assets(story_id)
    assert len(assets) == 1
    assert assets[0]["capability"] == "motion_poster"
    assert assets[0]["content_hash"] == "abc123hash"
    assert assets[0]["source"] == "manual_import"

    status = repo.get_status(story_id)
    assert status["asset_count"] == 1
