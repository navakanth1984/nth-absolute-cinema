# NAC Versioning Policy v1.0

**Status:** FROZEN (2026-07-03)

## Semver applies to every versioned artifact

```
MAJOR.MINOR.PATCH
```

- **MAJOR** — breaking change (a consumer written against the old version will not
  work unmodified).
- **MINOR** — additive, backward-compatible (new optional field, new event type, new
  node type that doesn't remove/rename anything).
- **PATCH** — clarification/bugfix in the spec text itself, no schema change.

## Per-artifact rules

### Creative Graph Specification versioning

- A `Story` node's `graph_spec_version` field pins that project to the schema version
  it was created under (`CREATIVE_GRAPH_SPEC.md` §1).
- MINOR bumps (e.g. 1.0 → 1.1) MAY add new optional fields to any node type or a new
  node type entirely; MUST NOT remove or rename an existing field.
- MAJOR bumps MAY remove/rename fields; a project on graph-spec 1.x is NOT
  automatically compatible with 2.0 — migration is an explicit, separate operation
  (out of scope for Sprint 0).

### Creative Compiler ABI versioning

- `CompilerDeclaration.abi_version` pins which ABI version a compiler implementation
  targets.
- A compiler targeting ABI 1.0 MUST continue to function against Creative Graph Spec
  1.x for any x — this is the guarantee `EXTENSIBILITY.md` states.
- Adding a 9th pipeline stage would be a MAJOR bump (breaks the "exactly 8 stages, no
  skipping" contract); adding an optional sub-step within an existing stage is MINOR.

### Pack versioning

- `PackDeclaration.pack_version` is independent of `PACK_ABI.md`'s own version
  (`abi_version`, added in Task 8's fix).
- A pack MAY bump its own `pack_version` (e.g. Google Flow pack 1.0 → 1.1) for
  prompt-quality improvements without any ABI change.
- `Provenance.pack_version` (`CREATIVE_GRAPH_SPEC.md` §9) always records the exact
  pack version used, so regenerating an old artifact can request that exact version
  if still installed, or the latest compatible one otherwise.

### `.nac` package versioning

- `manifest.nac_format_version` pins the container format itself (this document,
  Task 6).
- `manifest.graph_spec_version` pins the graph schema inside the package.
- Import compatibility rule: a NAC installation on graph-spec MAJOR version N can
  import any `.nac` package with `graph_spec_version` MAJOR ≤ N; importing a package
  from a newer MAJOR version MUST be rejected at manifest-verification time
  (`NAC_PACKAGE_SPEC.md` "Import rules" step 1), not partway through restoration.

### Plugin ABI versioning

- `Plugin.abi_version` pins which version of `PLUGIN_ABI.md` a plugin targets, same
  pattern as Compiler/Pack.
- A plugin targeting ABI 1.0 continues to receive events under Event Spec 1.x
  (`EXTENSIBILITY.md`).

### Event Specification versioning

- The event taxonomy (`EVENT_SPEC.md`) is a closed set at v1.0; adding a new
  `event_type` is a MINOR bump. Removing or renaming an existing `event_type` is a
  MAJOR bump — plugins subscribed via the old pattern would silently stop receiving
  events otherwise, which is exactly the failure mode semver MAJOR exists to signal.

## Cross-document consistency requirement

Every spec document under `docs/specs/v1/` that references another spec's type MUST
use that type's exact field names (verified during each task's self-review in this
plan). A future PATCH-level edit to fix a wording issue does not require re-verifying
every cross-reference; a MINOR or MAJOR edit to any spec document does.
