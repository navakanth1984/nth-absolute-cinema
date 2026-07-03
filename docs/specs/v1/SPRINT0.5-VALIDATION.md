# NAC Sprint 0.5 — Architecture Validation Gate

**Status:** GATE (2026-07-03)

This document is the architecture validation gate the user required before Sprint 1
may begin. It asks eight load-bearing questions about the frozen v1.0 spec set and
answers each with a concrete YES/NO grounded in a specific document, section, or
type — not an assertion. A single NO blocks the freeze until the architecture is
revised; Sprint 0 does not proceed to `SPRINT0_FREEZE.md` unless all eight are YES.

## The eight questions

**1. Can every compiler be replayed?**
**YES.** Every compiled `Asset`/`Prompt` node carries a full `Provenance` block
(`CREATIVE_GRAPH_SPEC.md` §9: `knowledge_version`, `compiler_id`, `compiler_version`,
`pack_id`, `pack_version`, `model`, `seed`, `output_hash`), and `COMPILER_ABI.md`'s
8-stage pipeline requires stage 8 (Export) to populate every field of that block —
"a missing or null Provenance field on an exported Asset/Prompt is a contract
violation, not a warning." Re-running the same 8 stages against the same
`knowledge_version` snapshot with the same `pack_version`/`model`/`seed` reproduces
the run.

**2. Can every artifact be traced to its source?**
**YES.** `Provenance.knowledge_version` (`CREATIVE_GRAPH_SPEC.md` §9) pins the exact
graph snapshot hash the artifact was compiled from, and `Provenance.output_hash`
identifies the artifact itself — together they answer "what graph state produced
this artifact" for any `Asset` or `Prompt` node, satisfying Manifesto principle 8.

**3. Can a new AI tool be added without modifying the engine?**
**YES.** `PACK_ABI.md`'s Capability Registry (`CapabilityRegistry.register()` /
`.resolve()`) lets `PromptCompiler` discover packs dynamically by
`target_platforms`/`requires_cloud` rather than importing a specific pack module —
"`PromptCompiler`... never imports a specific pack module directly." This is backed
by `MODULE_BOUNDARIES.md` rule 5: `engine.packs.*` may import `engine.kernel` only,
and rule 4: a compiler may import `engine.packs` only if it is the Prompt Compiler,
and even then only through the registry. A new pack is a new directory under
`engine/packs/`, discovered by presence (`PACK_ABI.md` §Pack discovery) — zero core
changes.

**4. Can a project move between machines by copying only the `.nac` package?**
**YES.** `NAC_PACKAGE_SPEC.md`'s import flow (steps 1-5) restores all five graphs,
genomes, provenance, and review history from the package alone; step 3 re-runs
`ComputeManager.profile_hardware()` + `select_profile()` fresh on the destination
machine (`COMPUTE_MANAGER_SPEC.md`, "never trusts the source manifest's
`exported_from_profile` as authoritative for the destination"); step 4 diffs
`manifest.referenced_local_models` against the destination's installed models and
calls `ModelManager.install()` only for the gap. No source-machine model weights or
cache are required to be present ahead of time. Cross-version import compatibility
itself is governed by `VERSIONING_POLICY.md` §`.nac` package versioning.

**5. Can the platform run fully offline?**
**YES.** Manifesto principle 5 ("Offline-first by default; cloud only when it adds
measurable value... cloud is an enhancement tier, never a requirement to produce a
minimum-viable artifact") is backed mechanically by `COMPUTE_MANAGER_SPEC.md`'s
`Micro` profile ("Lightweight local LLMs, local TTS, prompt compilation, story
generation, audio screenplay. Cloud video generation only when needed") and by
`PACK_ABI.md`'s `CapabilityMatrix.requires_cloud: bool` field, which lets
`CapabilityRegistry.resolve()` filter to cloud-independent packs when
`requires_cloud=False` is requested.

**6. Can every generation be reproduced?**
**YES.** `Provenance.seed` and `Provenance.model` (`CREATIVE_GRAPH_SPEC.md` §9)
capture the exact generation parameters, and `VERSIONING_POLICY.md` §Pack versioning
guarantees `Provenance.pack_version` "always records the exact pack version used, so
regenerating an old artifact can request that exact version if still installed, or
the latest compatible one otherwise" — reproduction is either byte-identical (same
pack version installed) or explicitly flagged as best-effort (compatible version
substituted), never silent.

**7. Can every compiler be replaced independently?**
**YES.** `MODULE_BOUNDARIES.md` rule 4 scopes each `engine.compilers.*` module to
import only `engine.kernel`, `engine.storage`, the five graph repository interfaces,
and `engine.model_manager` — no compiler imports another compiler. Independently,
`VERSIONING_POLICY.md` §Creative Compiler ABI versioning guarantees "a compiler
targeting ABI 1.0 MUST continue to function against Creative Graph Spec 1.x for any
x," meaning `CompilerDeclaration.abi_version` (`COMPILER_ABI.md` §Compiler
registration) is decoupled from `graph_spec_version` — a compiler can be swapped or
upgraded without the graph schema (or any other compiler) changing in lockstep.

**8. Can one graph evolve without breaking others?**
**YES.** `CREATIVE_GRAPH_SPEC.md` §1 defines five independent graphs
(`KnowledgeGraph`, `CinematicGraph`, `AssetGraph`, `ProductionGraph`,
`ReviewGraph`), and `MODULE_BOUNDARIES.md` rule 3 states the corresponding modules
"may import `engine.kernel` and `engine.storage` only — never each other directly
(cross-graph reactions go through `engine.kernel.EventBus`, per `EVENT_SPEC.md`)."
A change to one graph's schema (e.g. a MINOR bump adding a `CinematicGraph` field)
cannot introduce a compile-time or import-time dependency on another graph module,
because none is permitted to exist.

## Verdict

PASS — architecture may freeze
