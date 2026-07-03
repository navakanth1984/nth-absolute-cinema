from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.packs.capability_registry import resolve_capability, ExecutionMode


def test_resolve_motion_poster_is_ui_execution_and_available():
    entry = resolve_capability("motion_poster")
    assert entry.execution_mode == ExecutionMode.UI
    assert entry.available is True


def test_resolve_narration_premium_is_registered_but_unavailable():
    entry = resolve_capability("narration_premium")
    assert entry.execution_mode == ExecutionMode.API
    assert entry.available is False


def test_resolve_unknown_capability_raises():
    try:
        resolve_capability("nonexistent")
        assert False, "expected KeyError"
    except KeyError:
        pass
