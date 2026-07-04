# NAC Character Genome Specification v1.2

**Status:** FROZEN (2026-07-04)
**Governed by:** `MANIFESTO.md` principles 1, 2, 8; `CREATIVE_GRAPH_SPEC.md` §4
(Style Genome schema, Genome Composition Rule); `VERSIONING_POLICY.md`.
**Relationship to CREATIVE_GRAPH_SPEC.md:** this is a MINOR (additive,
backward-compatible) expansion of the `CharacterGenome` stub frozen in
`CREATIVE_GRAPH_SPEC.md` §4 (graph-spec 1.0 → 1.2). No field defined there is
removed or renamed - see §8 (Migration from graph-spec 1.0) for the exact
mapping. `VisualGenome`, `DialogueGenome`, and `CostumeGenome` remain
independently-versioned, independently-referenced node types exactly as
`CREATIVE_GRAPH_SPEC.md` §4 defines them - Character Genome composes them by
reference (`GenomeReference`, §3.7-3.9), never by embedding a copy, per the
universal Genome Composition Rule (`CREATIVE_GRAPH_SPEC.md` §4.1).

## 0. Philosophy

A Character Genome is **not** a character sheet. It is the canonical
representation of a character used by every department. Every department
reads from it; no department owns a duplicate copy; it evolves only through
approved reviews (recorded in `ReviewGraph`, `CREATIVE_GRAPH_SPEC.md` §7).

**Owning department:** Character (`CREATIVE_GRAPH_SPEC.md` §4.2). Only the
Character Department may write to `CharacterGenome` - every other department
listed in §4 below writes only to the one sub-genome it independently owns
(`DialogueGenome`, `VisualGenome`, `CostumeGenome`), never to `CharacterGenome`
itself.

**Reusable across projects** (`CREATIVE_GRAPH_SPEC.md` §4.4): a
`CharacterGenome` carries no `project_id`. The same genome ("Hanuman") may be
referenced by `Character` nodes in multiple projects - a feature film, a
sequel, a marketing campaign - without duplication. This is exactly why
Production/cost data does not live on the genome (§3.12 below) - embedding
project-specific cost data would make the genome non-portable.

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
├── visual_genome_ref: GenomeReference | None      → VisualGenome (v1.2: was bare UUID)
├── dialogue_genome_ref: GenomeReference | None    → DialogueGenome (v1.2: was bare UUID)
├── costume_genome_ref: GenomeReference | None     → CostumeGenome (v1.2: was bare UUID)
├── Behavior              (new in v1.1)
├── Knowledge             (new in v1.1)
└── VersionMetadata       (new in v1.1)
```

`GenomeReference` (`CREATIVE_GRAPH_SPEC.md` §4.3) = `{genome_id, genome_type,
version, status}`, not a bare UUID as originally drafted in v1.1 - this is
what makes replay possible ("Hanuman's `VisualGenome` at version 12,
approved" is pinned and resolvable). Production/cost data moved out of this
document entirely in v1.2 - see §3.12 and `CREATIVE_GRAPH_SPEC.md` §6's
`GenomeProductionRecord`.

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
visual_genome_ref: GenomeReference | None    # → VisualGenome node (CREATIVE_GRAPH_SPEC.md §4.3)
```
`VisualGenome` already carries `style_refs`, `negative_prompt`, `seed` -
unchanged. Google Flow / OpenArt / Higgsfield consume the referenced node at
the pinned `version`/`status`, not a copy on `CharacterGenome`.

### 3.8 Dialogue (by reference)
```
dialogue_genome_ref: GenomeReference | None  # → DialogueGenome node (CREATIVE_GRAPH_SPEC.md §4.3)
```
`DialogueGenome` already carries `vocabulary_profile`, `speech_pattern`.
**New optional fields added to `DialogueGenome` (MINOR bump, additive)** to
cover what the character-side design needs: `accent: str`, `language: str`,
`favorite_expressions: list[str]`, `humor: str`, `emotion_range: list[str]`,
`speech_rhythm: str`, `catchphrases: list[str]`, `forbidden_expressions:
list[str]`, `voice_seed: str | None` (the old stub's field, relocated here
since it's a dialogue/voice concern, not a general character field).
ElevenLabs / XTTS / Kokoro consume the referenced node. `DialogueGenome` is
owned by the Dialogue Department (`CREATIVE_GRAPH_SPEC.md` §4.2) - Character
Department may reference it but never write to it.

### 3.9 Costume (by reference)
```
costume_genome_ref: GenomeReference | None   # → CostumeGenome node (CREATIVE_GRAPH_SPEC.md §4.3)
```
Unchanged: `palette`, `material_refs`. Owned by the Costume Department.

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

### 3.12 Production - moved to ProductionGraph (v1.2 change)

v1.1 drafted a Production field group directly on `CharacterGenome`. **v1.2
moves this out entirely** to `CREATIVE_GRAPH_SPEC.md` §6's
`GenomeProductionRecord`, keyed by `(project_id, genome_id)` rather than
embedded on the genome. Rationale (`CREATIVE_GRAPH_SPEC.md` §4.4): a genome is
reusable across projects and carries no `project_id`; cost/GPU-time/asset
usage is inherently project-specific (the same Hanuman genome costs different
tokens to render in "Temple of Varuna" vs. a marketing campaign), so embedding
it here would make the genome non-portable. `review_status`/`approved`
likewise already live in `ReviewGraph` (§7) - `CharacterGenome` does not
duplicate them.

### 3.13 Version Metadata
Enables replay, matching `CREATIVE_GRAPH_SPEC.md`'s provenance/replay
principles (Manifesto principle 8).
```
genome_version: str             # this document's version, e.g. "1.2"
created_by: str
created_at: datetime
updated_at: datetime
review_history: list[ReviewEntry]   # ReviewGraph references, not copies
source_nodes: list[UUID]        # what this genome was compiled/derived from
compiler_version: str
content_hash: str               # sha256, for replay/diffing
```

## 4. Write authority

Per the Genome Composition Rule (`CREATIVE_GRAPH_SPEC.md` §4.1, point 6): only
the owning department may modify a genome. Applied here:

| Department | Reads | Writes |
|---|---|---|
| Story | CharacterGenome | Narrative section only (still Character-owned data - Story's write is scoped by convention/review, not by the Composition Rule, since Story does not *own* CharacterGenome) |
| Character | CharacterGenome | Everything (owning department, full authority) |
| Dialogue | CharacterGenome (via `dialogue_genome_ref`) | `DialogueGenome` only (Dialogue owns `DialogueGenome`, not `CharacterGenome` - §4.2) |
| Cinematography | CharacterGenome (via `visual_genome_ref`) | `VisualGenome` only (Cinematography owns `VisualGenome` - §4.2) |
| Costume | CharacterGenome (via `costume_genome_ref`) | `CostumeGenome` only (Costume owns `CostumeGenome` - §4.2) |
| Marketing | CharacterGenome | Prompt variants (derived output, never persisted back to any genome) |
| Production | - | Nothing on this genome - production data lives entirely in `ProductionGraph`'s `GenomeProductionRecord` (§3.12), which Production owns |

The Story row is the one exception worth calling out: it is not a genome
*owner* per §4.2, but is granted a narrow, review-gated write to the
Narrative section by convention (consistent with Story's role compiling the
Story Bible from character arcs). If this proves confusing in practice, the
cleaner long-term fix is a dedicated `NarrativeGenome` owned by Story and
referenced from `CharacterGenome` - not built now, flagged for Sprint 2C+ if
the Location/Story department work reveals it's needed.

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
| Production (via `GenomeProductionRecord`, `CREATIVE_GRAPH_SPEC.md` §6) | Production Department dashboards, cost prediction - not consumed from this document |

## 8. Migration from graph-spec 1.0's `CharacterGenome` stub

| Old field (graph-spec 1.0) | New location (graph-spec 1.2) |
|---|---|
| `visual_refs: list[AssetRef]` | Moved into the referenced `VisualGenome.style_refs` - `CharacterGenome` now holds `visual_genome_ref: GenomeReference` pointing to it |
| `voice_seed: str` | Moved into the referenced `DialogueGenome.voice_seed` (new field, §3.8) |
| `personality_traits: dict` | Superseded by the structured Psychological section (§3.3); a free-form `dict` remains acceptable as a legacy/unmigrated fallback for exactly one MINOR version, per `VERSIONING_POLICY.md`'s backward-compatibility rule |

No project on graph-spec 1.0 breaks: `character_id` stays the join key, old
fields are still readable, and none of the three old fields were removed -
only relocated to the reference targets they conceptually belonged to.

## 9. Migration from v1.1 draft (never merged - this document's own history)

| v1.1 draft | v1.2 (this frozen version) |
|---|---|
| `visual_genome_ref: UUID \| None` | `GenomeReference` (`{genome_id, genome_type, version, status}`) - §4.3 |
| `dialogue_genome_ref: UUID \| None` | `GenomeReference` |
| `costume_genome_ref: UUID \| None` | `GenomeReference` |
| §3.12 Production field group embedded on `CharacterGenome` | Moved to `CREATIVE_GRAPH_SPEC.md` §6 `GenomeProductionRecord`, keyed by `(project_id, genome_id)` |

v1.1 was never merged to `master` - this table exists for the record, not
because any shipped project depends on the v1.1 shape.
