from pathlib import Path
import sys
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.compilers.story_compiler import StoryCompiler


def test_run_produces_story_bible_provenance_and_metrics():
    fake_orchestrator = MagicMock()
    fake_orchestrator.model = "gemma2:9b"
    fake_orchestrator.generate.return_value = (
        "# Story Bible\n\nA sunken temple guards a secret.",
        {"provider": "OllamaProvider", "model": "gemma2:9b", "duration_s": 1.5, "tokens": 200, "attempts": 1},
    )

    compiler = StoryCompiler(orchestrator=fake_orchestrator)
    bible_text, provenance, metrics = compiler.run("A forgotten temple beneath the sea")

    assert "Story Bible" in bible_text
    fake_orchestrator.generate.assert_called_once()
    prompt_arg = fake_orchestrator.generate.call_args.args[0]
    assert "forgotten temple beneath the sea" in prompt_arg

    assert provenance.compiler_id == "story_compiler"
    assert provenance.model == "gemma2:9b"
    assert len(provenance.output_hash) == 64

    assert metrics["compiler"] == "story_compiler"
    assert metrics["tokens"] == 200
    assert metrics["provider"] == "OllamaProvider"
    assert metrics["output_hash"] == provenance.output_hash


def test_validate_rejects_empty_idea():
    compiler = StoryCompiler(orchestrator=MagicMock())
    results = compiler.validate("")
    assert any(not r.passed for r in results)
