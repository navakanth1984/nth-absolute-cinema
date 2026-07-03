# NAC Workspace Specification v1.0

**Status:** FROZEN (2026-07-03)
**Governed by:** `MANIFESTO.md` principle 5 (offline-first / portability is a
corollary: a project must work wherever the user is).

## Relocatable project root

The NAC project root (default `E:\nth-absolute-cinema\`, but not fixed to that path)
is resolved at startup by walking up from the running module's location to find a
marker file, `.nac-root`, rather than reading any configured or hardcoded path.

```
PathResolver {
  find_root(start_path: Path) -> Path            # walks up until .nac-root found
  resolve(relative: RelativePath) -> Path          # root-joined absolute path
  root() -> Path
}
```

**Hard rule:** no module outside `engine/kernel/paths.py` (or its language
equivalent) may construct an absolute path via string concatenation or a hardcoded
drive letter. Every other module receives paths only through `PathResolver.resolve()`
or a path already resolved and passed to it.

## Storage tiers

```
Cache tier    (cache/, renders/, assets/ [shared lib], temp/)
  — fully derived/regeneratable, safe to delete entirely, NEVER included in a
    .nac export (NAC_PACKAGE_SPEC.md "Never included")

Project tier  (projects/<project_id>/)
  — authoritative: five graphs (SQLite), genomes, provenance, review history,
    source assets. This is what a .nac package is built FROM.

Archive tier  (archive/)
  — cold storage: exported .nac packages, completed project snapshots kept for
    provenance/replay but not actively worked on.
```

Every path resolved by `PathResolver` MUST be tagged with which tier it belongs to;
`engine.storage` refuses to write project-tier data (graphs, provenance) into a
cache-tier path and vice versa — this is a load-bearing invariant for
`NAC_PACKAGE_SPEC.md`'s "export project tier only" rule to be mechanically
enforceable rather than a documentation-only convention.

## Relocation guarantee

Copying the entire project root (e.g. `E:\nth-absolute-cinema\` → a different drive
letter, or to another machine's `D:\nth-absolute-cinema\`) and re-running NAC from
the new location MUST work with zero configuration changes, provided:
1. The `.nac-root` marker file is copied along with everything else (it is at the
   project root, so a full-directory copy always includes it).
2. `local_models/` either comes along too, or Model Manager's on-demand install
   (`COMPUTE_MANAGER_SPEC.md`) fills gaps on first run at the new location.

This is the mechanism, not a promise made separately from the architecture — see
`SPRINT0_FREEZE.md` success criteria for the smoke test that verifies it.

## Multi-project workspace

One `E:\nth-absolute-cinema\` root MAY contain multiple projects under `projects/`
(one subdirectory per `project_id`). `cache/`, `local_models/`, and `archive/` are
shared across all projects in that workspace — this is why the cache tier is never
exported in a `.nac`: it may contain data belonging to sibling projects.
