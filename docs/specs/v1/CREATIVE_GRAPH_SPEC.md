# NAC Creative Graph Specification v1.0

**Status:** FROZEN (2026-07-03)
**Governed by:** `MANIFESTO.md` principles 1, 2, 8.

## 1. The five graphs

```
Project
├── KnowledgeGraph    — story facts, characters, mythology, locations, timeline
├── CinematicGraph    — shots, camera, cuts, music cues
├── AssetGraph        — images, audio, video, prompts (hashed, cached, reused)
├── ProductionGraph   — jobs, queues, cost/time estimates, dependencies
└── ReviewGraph       — approvals, comments, versions, human edits
```

`KnowledgeGraph` MUST NOT contain camera/edit decisions — those belong exclusively to
`CinematicGraph`. This is a hard schema-level separation, not a convention: no node
type defined under §2 (Knowledge) may carry a `camera_*`, `shot_type`, or `cut_*`
field.

## 2. Knowledge Graph node types

| Node type | Required fields | Notes |
|---|---|---|
| `Story` | `id: UUID`, `title: str`, `graph_spec_version: str` | Root node, one per project |
| `Act` | `id`, `story_id: UUID`, `order: int` | |
| `Sequence` | `id`, `act_id: UUID`, `order: int` | |
| `Scene` | `id`, `sequence_id: UUID`, `order: int`, `location_id: UUID` | |
| `Beat` | `id`, `scene_id: UUID`, `order: int`, `emotion: EmotionalNode` | Action/dialogue unit |
| `Character` | `id`, `name: str`, `genome_ref: UUID` | References `CharacterGenome` (§4) |
| `Location` | `id`, `name: str`, `genome_ref: UUID` | References `EnvironmentGenome` (§4) |
| `Prop` | `id`, `name: str`, `genome_ref: UUID` | |
| `StoryBible` | `id`, `story_id`, `content: dict` | World rules, mythology |

Story hierarchy is strictly non-linear at the presentation layer: `Story → Acts →
Sequences → Scenes → Beats` is the canonical ordering used for compilation, but
`ReviewGraph` (§6) may hold alternate orderings (Director's Cut, Trailer Cut) as
separate `Cut` nodes that reference the same `Beat` set with a different `order`
override — no `Beat` data is duplicated for an alternate cut.

### 2.1 Emotional Graph (embedded in every Beat)

```
EmotionalNode {
  audience_emotion: str
  character_emotion: dict[character_id: UUID, emotion: str]
  intensity: float        # 0.0-1.0
  pacing: float           # 0.0-1.0, 0=slow 1=fast
  conflict: float         # 0.0-1.0
  mystery: float          # 0.0-1.0
  release: float          # 0.0-1.0
}
```

## 3. Cinematic Graph node types

| Node type | Required fields | Notes |
|---|---|---|
| `Shot` | `id`, `beat_id: UUID`, `order: int`, `shot_type: str`, `camera_genome_ref: UUID`, `target_platforms: list[PlatformTarget]` | See §3.1 |
| `Cut` | `id`, `from_shot_id: UUID`, `to_shot_id: UUID`, `cut_type: str` | e.g. "hard", "fade", "wipe" |
| `MusicCue` | `id`, `shot_id: UUID`, `start_offset_ms: int`, `genome_ref: UUID` | References `MusicGenome` |

### 3.1 PlatformTarget (aspect-ratio-native generation)

```
PlatformTarget {
  platform: str            # "reels" | "youtube" | "linkedin" | "shorts" | ...
  aspect_ratio: str        # "9:16" | "16:9" | "1:1" | "4:5"
}
```

Each `Shot` carries `target_platforms: list[PlatformTarget]`. `COMPILER_ABI.md`'s
Prompt Compiler MUST generate one native prompt per `PlatformTarget` per shot —
composition and framing recomputed per ratio. Cropping a single master render to fit
multiple platforms is a spec violation, not an implementation choice.

## 4. Style Genome schema

Nine genome types, each independently versioned and referenced (never copied) by any
node needing consistency:

```
CharacterGenome { id, character_id, visual_refs: list[AssetRef], voice_seed: str, personality_traits: dict }
VisualGenome     { id, style_refs: list[AssetRef], negative_prompt: str, seed: int|None }
DialogueGenome   { id, character_id, vocabulary_profile: dict, speech_pattern: str }
MusicGenome      { id, tempo_range: tuple[int,int], instrumentation: list[str], mood_tags: list[str] }
EditingGenome    { id, pacing_profile: str, cut_frequency: float }
CameraGenome     { id, lens_preference: str, movement_style: str }
LightingGenome   { id, key_light_ratio: float, color_temp_k: int }
CostumeGenome    { id, character_id, palette: list[str], material_refs: list[AssetRef] }
EnvironmentGenome{ id, location_id, atmosphere_tags: list[str], palette: list[str] }
```

`AssetRef = { asset_id: UUID, content_hash: str }` — always a reference into
`AssetGraph` (§5), never an embedded binary.

## 5. Asset Graph node types

| Node type | Required fields | Notes |
|---|---|---|
| `Asset` | `id`, `content_hash: str (sha256)`, `kind: str`, `storage_tier: str`, `path: RelativePath` | `kind` ∈ {image, audio, video, prompt_text} |
| `Prompt` | `id`, `pack_id: str`, `pack_version: str`, `platform_target: PlatformTarget`, `compiled_text: str` | Output of Prompt Compiler |

Assets are content-addressed: two identical renders share one `Asset` node
(`content_hash` dedup) — this is the mechanism behind the "asset cache/reuse"
requirement in the design doc §5.

## 6. Production Graph node types

| Node type | Required fields |
|---|---|
| `Job` | `id`, `compiler_id: str`, `status: str`, `depends_on: list[UUID]` |
| `Estimate` | `id`, `job_id: UUID`, `estimated_tokens: int`, `estimated_gpu_hours: float`, `estimated_ram_mb: int`, `estimated_time_s: int`, `estimated_cost_usd: float`, `confidence: float` |

## 7. Review Graph node types

| Node type | Required fields |
|---|---|
| `ReviewEntry` | `id`, `artifact_id: UUID`, `stage: str`, `verdict: str`, `comment: str\|None`, `reviewer: str` | `stage` ∈ {ai_self_review, human_review}; `verdict` ∈ {approved, rejected, needs_revision} |
| `Cut` | `id`, `story_id: UUID`, `name: str`, `beat_order_override: list[UUID]` | Director's Cut / Trailer / alternate-ending views (§2) |

## 8. Four-layer validation contract

Every graph snapshot passes through, in order, before reaching any compiler:

```
Structural  → missing character, broken timeline, missing location
Creative    → inconsistent motivation, dialogue not matching CharacterGenome
Technical   → prompt exceeds pack token/duration limits (see PACK_ABI.md), invalid seed
Platform    → aspect ratio invalid for target platform, duration exceeds platform limit
```

A `ValidationResult` is `{ layer: str, passed: bool, violations: list[Violation] }`
per layer; a snapshot only proceeds to compilation if all four layers pass.

## 9. Provenance schema

Every compiled `Asset` and `Prompt` node carries:

```
Provenance {
  knowledge_version: str      # graph snapshot hash at compile time
  compiler_id: str
  compiler_version: str       # semver, see VERSIONING_POLICY.md
  pack_id: str | None
  pack_version: str | None
  model: str
  seed: int | None
  output_hash: str
}
```

## 10. Versioning of this schema

See `VERSIONING_POLICY.md` §Creative Graph Specification versioning. This document is
`v1.0`; a `graph_spec_version` field on the root `Story` node pins every project to
the schema version it was created under.
