from pathlib import Path
import sys
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.compilers.screenplay_compiler import ScreenplayCompiler


def test_run_produces_screenplay_provenance_and_metrics():
    fake_orchestrator = MagicMock()
    fake_orchestrator.model = "gemma2:9b"
    fake_orchestrator.generate.return_value = (
        "INT. SUNKEN TEMPLE - DAY\n\nWater drips.",
        {"provider": "OllamaProvider", "model": "gemma2:9b", "duration_s": 4.2, "tokens": 900, "attempts": 1},
    )

    compiler = ScreenplayCompiler(orchestrator=fake_orchestrator)
    screenplay_text, provenance, metrics = compiler.run(
        "# Story Bible\n\nA sunken temple.", target_runtime_minutes=15
    )

    assert "INT." in screenplay_text
    assert provenance.compiler_id == "screenplay_compiler"
    assert metrics["target_runtime_minutes"] == 15

    system_arg = fake_orchestrator.generate.call_args.kwargs["system"]
    assert "12-18" in system_arg or "15-minute" in system_arg


def test_validate_rejects_empty_bible():
    compiler = ScreenplayCompiler(orchestrator=MagicMock())
    results = compiler.validate("")
    assert any(not r.passed for r in results)
