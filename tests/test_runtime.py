from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.kernel.runtime import estimate_page_range


def test_estimate_page_range_for_15_minute_short():
    low, high = estimate_page_range(15)
    assert low == 12
    assert high == 18


def test_estimate_page_range_for_feature_length():
    low, high = estimate_page_range(130)
    assert low == 104
    assert high == 156
