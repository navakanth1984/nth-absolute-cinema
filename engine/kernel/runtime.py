"""Deterministic runtime -> screenplay page-count estimate (Tier 0 per TITAN's
routing philosophy - Python, not an LLM call). Standard screenplay rule of thumb:
~1 page per minute of screen time. This is what lets the same Screenplay Compiler
target a 15-minute short today and a 130-page feature later by changing the project's
target_runtime_minutes constraint, not by rewriting prompts."""
from __future__ import annotations

PAGES_PER_MINUTE = 1.0


def estimate_page_range(target_runtime_minutes: int) -> tuple[int, int]:
    target_pages = target_runtime_minutes * PAGES_PER_MINUTE
    low = max(1, round(target_pages * 0.8))
    high = round(target_pages * 1.2)
    return low, high
