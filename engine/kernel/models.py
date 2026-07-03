"""Shared dataclasses whose field names are fixed by CREATIVE_GRAPH_SPEC.md.
Every other module imports Provenance/Estimate from here - never redefines them."""
from __future__ import annotations

from dataclasses import dataclass, field
import uuid


@dataclass
class Provenance:
    knowledge_version: str
    compiler_id: str
    compiler_version: str
    model: str
    output_hash: str
    pack_id: str | None = None
    pack_version: str | None = None
    seed: int | None = None


@dataclass
class Estimate:
    job_id: str
    estimated_tokens: int
    estimated_gpu_hours: float
    estimated_ram_mb: int
    estimated_time_s: int
    estimated_cost_usd: float
    confidence: float
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
