# NAC Character Genome Specification v1.1

**Status:** FROZEN (2026-07-04)
**Governed by:** `MANIFESTO.md` principles 1, 2, 8; `CREATIVE_GRAPH_SPEC.md` §4
(Style Genome schema); `VERSIONING_POLICY.md`.
**Relationship to CREATIVE_GRAPH_SPEC.md:** this is a MINOR (additive,
backward-compatible) expansion of the `CharacterGenome` stub frozen in
`CREATIVE_GRAPH_SPEC.md` §4 (graph-spec 1.0 → 1.1). No field defined there is
removed or renamed - see §8 (Migration from graph-spec 1.0) for the exact
mapping. `VisualGenome`, `DialogueGenome`, and `CostumeGenome` remain
independently-versioned, independently-referenced node types exactly as
`CREATIVE_GRAPH_SPEC.md` §4 defines them - Character Genome composes them by
reference, never by embedding a copy.

## 0. Philosophy

A Character Genome is **not** a character sheet. It is the canonical
representation of a character used by every department. Every department
reads from it; no department owns a duplicate copy; it evolves only through
approved reviews (recorded in `ReviewGraph`, `CREATIVE_GRAPH_SPEC.md` §6).

**Naming split (deliberate, not an inconsistency):**
- **UI (Director Studio):** "Character Bible" - filmmakers already understand this term.
- **SDK / Knowledge Graph / Documentation:** `CharacterGenome` - precise, matches
  the existing Style Genome family's naming (`VisualGenome`, `DialogueGenome`, etc.).

## 1. What Character Genome must NOT contain

Scenes, camera, lighting, music, editing, timeline, shot lists. Those belong
to `CinematicGraph` (`CREATIVE_GRAPH_SPEC.md` §3) and their respective
departments. A `CharacterGenome` node carrying a `camera_*`, `shot_type`, or
`cut_*` field is a spec violation, per the same hard rule §1 of
`CREATIVE_GRAPH_SPEC.md` already applies to `KnowledgeGraph`.

## 2. Structure

```
CharacterGenome
├── Identity              (new in v1.1)
├── Physical              (new in v1.1)
├── Psychological         (new in v1.1 - supersedes old personality_traits: dict)
├── Narrative             (new in v1.1)
├── Relationship          (new in v1.1 - becomes CreativeKnowledgeGraph edges, §5)
├── Performance           (new in v1.1)
├── visual_genome_ref: UUID | None      → VisualGenome (referenced, not embedded)
├── dialogue_genome_ref: UUID | None    → DialogueGenome (referenced, not embedded)
├── costume_genome_ref: UUID | None     → CostumeGenome (referenced, not embedded)
├── Behavior              (new in v1.1)
├── Knowledge             (new in v1.1)
├── Production            (new in v1.1 - NAC-specific, not a filmmaking convention)
└── VersionMetadata       (new in v1.1)
```

Everything the old stub covered still exists: `visual_refs` now lives inside
the referenced `VisualGenome.style_refs`; `voice_seed` lives inside the
referenced `DialogueGenome` (new optional field, see §8); `personality_traits`
is superseded by the richer Psychological section below (old dict form
remains readable for one migration cycle per §8).

## 3. Field groups

### 3.1 Identity
```
character_id: UUID
canonical_name: str
aliases: list[str]
titles: list[str]
species: str
age: int | str            # str allows "unknown"/"ageless"/a range
gender: str
birthplace: str
occupation: str
status: str                # e.g. alive/deceased/unknown
tags: list[str]
```

### 3.2 Physical
Purpose: every image model must generate the same character.
```
height: str
body_type: str
face: str
eyes: str
hair: str
skin: str
clothing: str               # default/canonical outfit description
accessories: list[str]
scars: list[str]
symbols: list[str]
color_palette: list[str]
```

### 3.3 Psychological
```
core_personality: str
strengths: list[str]
weaknesses: list[str]
motivations: list[str]
desires: list[str]
needs: list[str]
greatest_fear: str
trauma: str | None
beliefs: list[str]
values: list[str]
moral_alignment: str
internal_conflict: str
```

### 3.4 Narrative
```
role: str                   # hero/mentor/villain/supporting/comic_relief/...
narrative_function: str
beginning_state: str
ending_state: str
arc: str
milestones: list[str]
secrets: list[str]
reveals: list[str]
```

### 3.5 Relationship
Structural note: this section is **not** stored as a flat field on
`CharacterGenome` - each entry becomes a graph edge between two `Character`
nodes (or a `Character` and an org/faction node), per `CREATIVE_GRAPH_SPEC.md`
§6's edge conventions. Listed here as the field group a director edits in the
Character Workspace; the persistence shape is edges, not embedded lists.
```
parents, children, friends, enemies, mentors, students: list[character_id]
romantic, political, religious, organizational: list[character_id]
relationship_strength: dict[character_id, float]   # 0.0-1.0
relationship_history: dict[character_id, str]
```

### 3.6 Performance
Purpose: future animation systems consume this.
```
energy: str
movement: str
posture: str
walking_style: str
gestures: list[str]
expressions: list[str]
reaction_patterns: list[str]
combat_style: str | None
presence: str
silence_style: str
```

### 3.7 Visual (by reference)
```
visual_genome_ref: UUID | None    # → VisualGenome node (CREATIVE_GRAPH_SPEC.md §4)
```
`VisualGenome` already carries `style_refs`, `negative_prompt`, `seed` -
unchanged. Google Flow / OpenArt / Higgsfield consume the referenced node, not
a copy on `CharacterGenome`.

### 3.8 Dialogue (by reference)
```
dialogue_genome_ref: UUID | None  # → DialogueGenome node (CREATIVE_GRAPH_SPEC.md §4)
```
`DialogueGenome` already carries `vocabulary_profile`, `speech_pattern`.
**New optional fields added to `DialogueGenome` (MINOR bump, additive)** to
cover what the character-side design needs: `accent: str`, `language: str`,
`favorite_expressions: list[str]`, `humor: str`, `emotion_range: list[str]`,
`speech_rhythm: str`, `catchphrases: list[str]`, `forbidden_expressions:
list[str]`, `voice_seed: str | None` (the old stub's field, relocated here
since it's a dialogue/voice concern, not a general character field).
ElevenLabs / XTTS / Kokoro consume the referenced node.

### 3.9 Costume (by reference)
```
costume_genome_ref: UUID | None   # → CostumeGenome node (CREATIVE_GRAPH_SPEC.md §4)
```
Unchanged: `palette`, `material_refs`.

### 3.10 Behavior
```
habits: list[str]
routines: list[str]
decision_style: str
leadership_style: str | None
learning_style: str
risk_profile: str
stress_response: str
conflict_response: str
love_language: str | None
social_style: str
```

### 3.11 Knowledge
```
known_facts: list[str]
unknown_facts: list[str]       # dramatic irony hooks
secrets: list[str]
skills: list[str]
languages: list[str]
education: str | None
profession: str
magic: list[str] | None
technology: list[str] | None
combat: list[str] | None
religion: str | None
culture: str | None
```

### 3.12 Production (NAC-specific, not a filmmaking convention)
```
approved: bool
review_status: str              # matches ReviewGraph verdict values
version: int
last_updated: datetime
generated_assets: list[AssetRef]
voice_assets: list[AssetRef]
image_assets: list[AssetRef]
prompt_assets: list[AssetRef]
scene_usage: list[scene_id]
shot_usage: list[shot_id]
estimated_cost_usd: float
estimated_tokens: int
gpu_time_s: float
```

### 3.13 Version Metadata
Enables replay, matching `CREATIVE_GRAPH_SPEC.md`'s provenance/replay
principles (Manifesto principle 8).
```
genome_version: str             # this document's version, e.g. "1.1"
created_by: str
created_at: datetime
updated_at: datetime
review_history: list[ReviewEntry]   # ReviewGraph references, not copies
source_nodes: list[UUID]        # what this genome was compiled/derived from
compiler_version: str
content_hash: str               # sha256, for replay/diffing
```

## 4. Write authority

| Department | Reads | Writes |
|---|---|---|
| Story | Character Genome | Narrative section only |
| Character | Character Genome | Everything (full authority) |
| Dialogue | Character Genome | `dialogue_genome_ref` target only |
| Cinematography | Character Genome | `visual_genome_ref` target only |
| Audio (Narration/Music/Sound Design) | Character Genome | Voice-related fields inside `DialogueGenome` only |
| Marketing | Character Genome | Prompt variants (derived, not persisted back to the genome) |
| Production | Character Genome | Production section only |

Only the Character Department has full write authority over the genome.
Every other department's write is scoped to the one referenced sub-genome or
section it owns, and every write is subject to `ReviewGraph` approval - this
mirrors `CREATIVE_GRAPH_SPEC.md`'s existing separation-of-concerns rule (§1)
rather than introducing a new enforcement mechanism.

## 5. Relationship Genome → graph edges

Per §3.5: relationship data is never stored as a flat list on the
`CharacterGenome` node itself. Each relationship becomes an edge in the
Knowledge Graph between two `Character` nodes (or a `Character` and an
org/faction node where one exists), carrying `relationship_type`,
`relationship_strength`, and `relationship_history` as edge attributes. This
keeps relationships queryable as a graph (e.g. "who are Amrita's enemies"
becomes a graph traversal, not a manual list scan) and consistent with how
`CinematicGraph` and `AssetGraph` already model connections as edges rather
than embedded arrays.

## 6. What Character Genome should NOT contain (restated from §1)

Scenes, camera, lighting, music, editing, timeline, shot lists.

## 7. Consumers

| Genome / section | Consumed by |
|---|---|
| Identity, Physical | Character Workspace, Casting/reference display |
| Psychological, Narrative | Story Department (consistency checks), Screenplay Department (assembly, not invention - `CREATIVE_GRAPH_SPEC.md` §2's non-linear story hierarchy) |
| Relationship (edges) | Story Department, Screenplay Department |
| Performance | Future animation systems (not built yet - reference-only field group until an Animation/Cinematography consumer exists) |
| `visual_genome_ref` → VisualGenome | Google Flow, OpenArt, Higgsfield packs |
| `dialogue_genome_ref` → DialogueGenome | ElevenLabs, XTTS, Kokoro |
| `costume_genome_ref` → CostumeGenome | Wardrobe/asset-generation prompts |
| Production | Production Department dashboards, cost prediction |

## 8. Migration from graph-spec 1.0's `CharacterGenome` stub

| Old field (graph-spec 1.0) | New location (graph-spec 1.1) |
|---|---|
| `visual_refs: list[AssetRef]` | Moved into the referenced `VisualGenome.style_refs` - `CharacterGenome` now holds `visual_genome_ref` pointing to it |
| `voice_seed: str` | Moved into the referenced `DialogueGenome.voice_seed` (new field, §3.8) |
| `personality_traits: dict` | Superseded by the structured Psychological section (§3.3); a free-form `dict` remains acceptable as a legacy/unmigrated fallback for exactly one MINOR version, per `VERSIONING_POLICY.md`'s backward-compatibility rule |

No project on graph-spec 1.0 breaks: `character_id` stays the join key, old
fields are still readable, and none of the three old fields were removed -
only relocated to the reference targets they conceptually belonged to.
