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
CharacterGenome { id, character_id, visual_genome_ref: UUID|None, dialogue_genome_ref: UUID|None,
                  costume_genome_ref: UUID|None, ... }  # full schema: CHARACTER_GENOME_SPEC.md (v1.1, MINOR bump)
VisualGenome     { id, style_refs: list[AssetRef], negative_prompt: str, seed: int|None }
DialogueGenome   { id, character_id, vocabulary_profile: dict, speech_pattern: str, voice_seed: str|None,
                  accent, language, favorite_expressions, humor, emotion_range, speech_rhythm,
                  catchphrases, forbidden_expressions }  # fields added in CHARACTER_GENOME_SPEC.md §3.8, MINOR bump
MusicGenome      { id, tempo_range: tuple[int,int], instrumentation: list[str], mood_tags: list[str] }
EditingGenome    { id, pacing_profile: str, cut_frequency: float }
CameraGenome     { id, lens_preference: str, movement_style: str }
LightingGenome   { id, key_light_ratio: float, color_temp_k: int }
CostumeGenome    { id, character_id, palette: list[str], material_refs: list[AssetRef] }
EnvironmentGenome{ id, location_id, atmosphere_tags: list[str], palette: list[str] }
```

`CharacterGenome`'s full structure (Identity/Physical/Psychological/Narrative/
Relationship/Performance/Behavior/Knowledge/VersionMetadata field groups and
the graph-spec-1.0→1.1 field migration) is specified in full in
`CHARACTER_GENOME_SPEC.md` rather than inline here - this is a MINOR
(additive) expansion per `VERSIONING_POLICY.md`, not a breaking change to this
frozen document. UI label: "Character Bible"; SDK/graph/docs: `CharacterGenome`.
Production/cost data for a genome lives in `ProductionGraph` (§6), never
inside the genome itself - see §4.3.

### 4.1 Genome Composition Rule (universal - graph-spec 1.2, applies to every genome type)

1. A Genome may own only the information belonging to its Department.
2. A Genome may reference any number of other Genomes.
3. A Genome shall never embed another Genome.
4. Every Genome is independently versioned.
5. Every Genome has exactly one owning Department.
6. Only the owning Department may modify that Genome.
7. Other Departments reference the latest **approved** version - not the
   latest version unconditionally, since an unapproved edit should not
   propagate to consumers until `ReviewGraph` (§7) records approval.

This generalizes the reference-not-copy rule already stated for the nine
genome types below (previously scoped only to "never copied" - now explicit
about versioning, ownership, and approval-gating) and is not
Character-Genome-specific: it governs `VisualGenome`, `DialogueGenome`,
`CostumeGenome`, `CameraGenome`, `MusicGenome`, `LightingGenome`,
`EditingGenome`, and `EnvironmentGenome` identically.

### 4.2 Genome ownership

| Genome | Owning Department |
|---|---|
| `CharacterGenome` | Character |
| `DialogueGenome` | Dialogue |
| `CostumeGenome` | Costume |
| `VisualGenome` | Cinematography |
| `CameraGenome` | Cinematography |
| `LightingGenome` | Cinematography |
| `MusicGenome` | Music |
| `EditingGenome` | Editing |
| `EnvironmentGenome` | Location |

A department not listed here that needs to read a genome does so via a
`GenomeReference` (below) - it never writes to a genome it does not own.

### 4.3 GenomeReference (replaces bare `*_genome_ref: UUID` fields)

```
GenomeReference {
  genome_id: UUID
  genome_type: str       # e.g. "VisualGenome" - which of the nine types
  version: int
  status: str            # matches ReviewGraph verdict values - "approved" is
                          # the only status other departments may consume per
                          # the Composition Rule's point 7
}
```

Any field previously typed `some_genome_ref: UUID` (e.g.
`CharacterGenome.visual_genome_ref` in `CHARACTER_GENOME_SPEC.md` §3.7-3.9) is
now typed `GenomeReference` instead - this is what makes replay possible
("Hanuman's `VisualGenome` at version 12, approved" is a resolvable, pinned
reference; a bare UUID with no version is not). MINOR bump, additive: a
`GenomeReference` with `version` unset/None behaves as "latest approved," so
existing bare-UUID-shaped callers are not broken, only under-specified
compared to what's now possible.

### 4.4 Genome reusability across projects

A Genome (e.g. a `CharacterGenome` for "Hanuman") carries no `project_id` and
is not owned by any single project - it is the project-specific `Character`
node (§2) that references a genome via `genome_ref`/`GenomeReference`. The
same `CharacterGenome` may be referenced by `Character` nodes in multiple
projects ("Temple of Varuna," "Ramayana," a marketing campaign) without
duplication. This is why Production data (cost, GPU time, scene/shot usage -
all inherently project-specific) must live in `ProductionGraph` keyed by
`(project_id, genome_id)`, never embedded in the genome: embedding it would
make the genome non-portable across projects, defeating reuse.

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
| `GenomeProductionRecord` | `id`, `project_id: UUID`, `genome_id: UUID`, `genome_type: str`, `generated_assets: list[AssetRef]`, `scene_usage: list[UUID]`, `shot_usage: list[UUID]`, `estimated_cost_usd: float`, `estimated_tokens: int`, `gpu_time_s: float` | Per §4.4: production/cost data for *any* genome, keyed by `(project_id, genome_id)` - not embedded in the genome itself, so the same genome stays portable across projects. Supersedes the "Production" field group originally drafted inline on `CharacterGenome` in `CHARACTER_GENOME_SPEC.md`. |

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
`v1.2` (1.0 → 1.1: `CharacterGenome`/`DialogueGenome` field expansion, see
`CHARACTER_GENOME_SPEC.md`; 1.1 → 1.2: universal Genome Composition Rule §4.1,
genome ownership §4.2, `GenomeReference` §4.3, genome reusability §4.4,
`GenomeProductionRecord` §6 - all additive, no field removed or renamed). A
`graph_spec_version` field on the root `Story` node pins every project to the
schema version it was created under.
