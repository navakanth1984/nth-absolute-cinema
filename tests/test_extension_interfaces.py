from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.extensions.interfaces import (
    CreditEstimator,
    ProviderAdapter,
    CreativeExecutionPlanner,
    FeedbackEngine,
)


def test_extension_interfaces_cannot_be_instantiated_directly():
    for cls in (CreditEstimator, ProviderAdapter, CreativeExecutionPlanner, FeedbackEngine):
        try:
            cls()
            assert False, f"{cls.__name__} should be abstract"
        except TypeError:
            pass
