from pathlib import Path
import sys
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.compilers.audio_compiler import AudioCompiler


def test_run_produces_audio_file_provenance_and_metrics(tmp_path):
    fake_tts = MagicMock()
    out_path = tmp_path / "screenplay_audio.wav"
    fake_tts.synthesize.return_value = out_path

    compiler = AudioCompiler(tts_provider=fake_tts)
    result_path, provenance, metrics = compiler.run(
        "INT. TEMPLE - DAY\n\nWater drips.", out_path
    )

    assert result_path == out_path
    fake_tts.synthesize.assert_called_once()
    narration_arg = fake_tts.synthesize.call_args.args[0]
    assert "Water drips" in narration_arg
    assert "INT." not in narration_arg

    assert provenance.compiler_id == "audio_compiler"
    assert provenance.model == "pyttsx3"
    assert metrics["execution_mode"] == "local"


def test_validate_rejects_empty_screenplay():
    compiler = AudioCompiler(tts_provider=MagicMock())
    results = compiler.validate("")
    assert any(not r.passed for r in results)
