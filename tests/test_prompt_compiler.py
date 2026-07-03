from pathlib import Path
import sys
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.compilers.prompt_compiler import PromptCompiler


def test_run_produces_motion_poster_prompt_provenance_and_metrics():
    fake_orchestrator = MagicMock()
    fake_orchestrator.model = "gemma2:9b"
    fake_orchestrator.generate.return_value = (
        "A sunken stone temple glowing with bioluminescent light, cinematic, 16:9",
        {"provider": "OllamaProvider", "model": "gemma2:9b", "duration_s": 2.1, "tokens": 60, "attempts": 1},
    )

    compiler = PromptCompiler(orchestrator=fake_orchestrator)
    prompt_text, provenance, metrics = compiler.run("INT. SUNKEN TEMPLE - DAY\n\nWater drips.")

    assert "16:9" in prompt_text
    assert provenance.compiler_id == "prompt_compiler"
    assert provenance.pack_id == "google_flow_mvp"
    assert metrics["execution_mode"] == "ui"
    assert metrics["target_provider"] == "google_flow_mvp"


def test_validate_rejects_empty_screenplay():
    compiler = PromptCompiler(orchestrator=MagicMock())
    results = compiler.validate("")
    assert any(not r.passed for r in results)
