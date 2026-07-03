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


def test_create_story_defaults_target_runtime_to_15_minutes(tmp_path):
    conn = init_db(tmp_path / "test.db")
    repo = KnowledgeRepo(conn)
    story_id = repo.create_story("An idea")
    assert repo.get_story(story_id)["target_runtime_minutes"] == 15


def test_create_story_accepts_custom_runtime(tmp_path):
    conn = init_db(tmp_path / "test.db")
    repo = KnowledgeRepo(conn)
    story_id = repo.create_story("An idea", target_runtime_minutes=130)
    assert repo.get_story(story_id)["target_runtime_minutes"] == 130


def test_save_and_get_compiler_metrics(tmp_path):
    conn = init_db(tmp_path / "test.db")
    repo = KnowledgeRepo(conn)
    story_id = repo.create_story("An idea")

    repo.save_compiler_metrics(story_id, "StoryCompiler", {"tokens": 100, "duration_s": 1.2})
    repo.save_compiler_metrics(story_id, "ScreenplayCompiler", {"tokens": 300, "duration_s": 3.4})

    metrics = repo.get_compiler_metrics(story_id)
    assert len(metrics) == 2
    assert metrics[0]["compiler"] == "StoryCompiler"
    assert metrics[0]["tokens"] == 100
    assert metrics[1]["compiler"] == "ScreenplayCompiler"
