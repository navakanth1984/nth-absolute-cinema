"""Minimal Capability Registry - full PACK_ABI.md CapabilityMatrix/CapabilityRegistry
machinery is Sprint 2+ (docs/specs/v1/PACK_ABI.md). This is the lightweight subset
that lets compilers stay provider-agnostic in Sprint 1: a static lookup of which
provider handles which capability, and whether it's local/api/ui execution.

UI-execution entries (google_flow, elevenlabs) are registered as available=False -
NAC does not have real integrations for them yet, but registering the shape now
means a future pack fills in an entry here without any compiler code changing.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExecutionMode(str, Enum):
    LOCAL = "local"
    API = "api"
    UI = "ui"


@dataclass(frozen=True)
class CapabilityEntry:
    provider_id: str
    execution_mode: ExecutionMode
    supports: tuple[str, ...]
    available: bool


CAPABILITY_REGISTRY: dict[str, CapabilityEntry] = {
    "screenplay": CapabilityEntry(
        provider_id="ollama_or_openrouter",
        execution_mode=ExecutionMode.LOCAL,
        supports=("story_bible", "screenplay"),
        available=True,
    ),
    "narration": CapabilityEntry(
        provider_id="pyttsx3",
        execution_mode=ExecutionMode.LOCAL,
        supports=("audio_screenplay",),
        available=True,
    ),
    "motion_poster": CapabilityEntry(
        provider_id="google_flow_mvp",
        execution_mode=ExecutionMode.UI,
        supports=("motion_poster_prompt",),
        available=True,  # produces a prompt package for manual paste into Google Flow's UI
    ),
    "narration_premium": CapabilityEntry(
        provider_id="elevenlabs",
        execution_mode=ExecutionMode.API,
        supports=("narration", "dialogue"),
        available=True,  # ElevenLabs is now fully integrated as an API provider
    ),
    "soundtrack": CapabilityEntry(
        provider_id="google_flow_music",
        execution_mode=ExecutionMode.UI,
        supports=("soundtrack", "ambience"),
        available=False,  # not integrated yet - same reasoning as narration_premium
    ),
}


def resolve_capability(capability: str) -> CapabilityEntry:
    if capability not in CAPABILITY_REGISTRY:
        raise KeyError(f"No capability registered for '{capability}'")
    return CAPABILITY_REGISTRY[capability]
