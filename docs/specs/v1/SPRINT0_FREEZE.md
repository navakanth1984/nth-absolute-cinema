# NAC Sprint 0 — Architecture Freeze Declaration

**Status:** FROZEN (2026-07-03)

## What is frozen as of this document

| Document | Version | Governs |
|---|---|---|
| `MANIFESTO.md` | v1.0 | Philosophy — 8 principles every compiler/pack/plugin must obey |
| `CREATIVE_GRAPH_SPEC.md` | v1.0 | Five graphs, Style Genome, story hierarchy, 4-layer validation, provenance |
| `COMPILER_ABI.md` | v1.0 | 8-stage compiler contract, estimation, provenance, review contracts |
| `PACK_ABI.md` | v1.0 | Generation-tool integration contract, CapabilityMatrix, discovery |
| `NAC_PACKAGE_SPEC.md` | v1.0 | `.nac` container format, export/import rules, integrity |
| `EVENT_SPEC.md` | v1.0 | Event envelope, taxonomy, delivery guarantees |
| `PLUGIN_ABI.md` | v1.0 | Cross-cutting extension contract, hard constraints |
| `WORKSPACE_SPEC.md` | v1.0 | Relocatable root, storage tiers, multi-project workspace |
| `COMPUTE_MANAGER_SPEC.md` | v1.0 | Hardware profiles, profiling contract, on-demand model install |
| `MODULE_BOUNDARIES.md` | v1.0 | Import dependency diagram + 9 allowed-import rules |
| `REPOSITORY_INTERFACES.md` | v1.0 | `Protocol` stubs for every cross-module interface |
| `EXTENSIBILITY.md` | v1.0 | 3 extension points, compatibility guarantees |
| `VERSIONING_POLICY.md` | v1.0 | Semver rules for graph spec, compiler ABI, pack, `.nac`, plugin, event spec |
| `SPRINT0.5-VALIDATION.md` | v1.0 | The 8-question architecture validation gate that precedes this freeze |

## Success criteria for Sprint 0

- [x] All 14 documents above exist under `E:\nth-absolute-cinema\docs\specs\v1\`,
  each marked FROZEN, each committed to git.
- [x] Zero placeholder/TBD text anywhere in `docs/specs/v1/` (verified by Task 13
  Step 1's consistency pass).
- [x] Every cross-document type reference resolves to exactly one canonical
  definition with matching field names (verified by Task 13 Step 1).
- [x] Sprint 0.5 validation (`SPRINT0.5-VALIDATION.md`) passed all 8
  architecture-guarantee questions — replay, traceability, tool extensibility,
  machine portability, offline operation, generation reproducibility, independent
  compiler replacement, and independent graph evolution are each grounded YES, not
  asserted.
- [x] The `navakanth001` repo's original design doc
  (`docs/superpowers/specs/2026-07-03-nth-absolute-cinema-design.md`) and this
  freeze do not contradict each other on any point — this freeze is the formal spec
  text for what that design doc already approved, not a redesign (verified by Task
  14).
- [x] `E:\nth-absolute-cinema\` exists as an initialized git repository with the
  full Task-1 directory scaffold present.
- [x] No engine code (Python modules under `engine/`) exists yet — Sprint 0 produces
  specs only.

## Non-goals for Sprint 0

- No compiler, pack, or plugin implementation — Sprint 1 begins the Kernel and first
  real code.
- No Compute Manager threshold values (exact GB/VRAM cutoffs for profile selection)
  — the *function signature* is frozen (`COMPUTE_MANAGER_SPEC.md`), the *thresholds*
  are a Sprint 1 implementation decision, not an architecture-freeze decision.
- No dashboard, no CLI, no API server — `engine.api` boundary is declared in
  `MODULE_BOUNDARIES.md` but not built.
- No CI/lint enforcement of the import rules in `MODULE_BOUNDARIES.md` — that's a
  Sprint 1 tooling task once there's code to lint.
- No `.nac` file has actually been produced or imported — the format is specified,
  not exercised, until Sprint 6 per the design doc's sprint plan.
- No changes to `docs/vision/TITAN.md` or the CRP repo — reconfirmed out of scope.

## Next step

Sprint 1 (per `docs/superpowers/specs/2026-07-03-nth-absolute-cinema-design.md`
§23/§17): Kernel (`engine.kernel.paths` implementing `PathResolver`), Knowledge Graph,
Storage (3 tiers), Model Manager with on-demand install, Compute Manager — all built
directly against the 14 documents frozen here, with no further architecture
discussion required to start.
