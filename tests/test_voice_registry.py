from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.packs.capability_registry import resolve_capability, ExecutionMode


def test_voice_registry_capabilities():
    # Verify local narration capability
    narration = resolve_capability("narration")
    assert narration.provider_id == "pyttsx3"
    assert narration.execution_mode == ExecutionMode.LOCAL
    assert narration.available is True
    assert "audio_screenplay" in narration.supports

    # Verify premium narration capability (ElevenLabs)
    narration_premium = resolve_capability("narration_premium")
    assert narration_premium.provider_id == "elevenlabs"
    assert narration_premium.execution_mode == ExecutionMode.API
    assert narration_premium.available is True
    assert "narration" in narration_premium.supports
    assert "dialogue" in narration_premium.supports
