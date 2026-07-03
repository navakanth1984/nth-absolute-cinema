from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.storage.db import init_db
from engine.storage.knowledge_repo import KnowledgeRepo


def test_create_story_and_round_trip(tmp_path):
    db_path = tmp_path / "test.db"
    conn = init_db(db_path)
    repo = KnowledgeRepo(conn)

    story_id = repo.create_story("A forgotten temple beneath the sea")
    assert story_id

    story = repo.get_story(story_id)
    assert story["idea_text"] == "A forgotten temple beneath the sea"
    assert story["story_bible"] is None
    assert story["screenplay"] is None

    repo.save_story_bible(story_id, "# Story Bible\n...")
    repo.save_screenplay(story_id, "INT. TEMPLE - DAY\n...")

    story = repo.get_story(story_id)
    assert story["story_bible"] == "# Story Bible\n..."
    assert story["screenplay"] == "INT. TEMPLE - DAY\n..."
