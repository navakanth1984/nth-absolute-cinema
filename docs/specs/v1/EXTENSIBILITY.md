# NAC Extension Points & Compatibility Guarantees v1.0

**Status:** FROZEN (2026-07-03)

## The three extension points (closed set for v1.0)

```
1. NAC Pack       — new generation tool integration (PACK_ABI.md)
2. Plugin         — cross-cutting event-driven behavior (PLUGIN_ABI.md)
3. Compiler       — new artifact type / new domain (COMPILER_ABI.md)
```

No other extension mechanism exists in v1.0 — a feature that doesn't fit one of
these three either belongs in `engine.kernel` (core) or is out of scope for Phase 1
(see design doc §24 non-goals).

## Compatibility guarantees

| Guarantee | Scope |
|---|---|
| A Pack built against Pack ABI v1.0 works with any Compiler ABI v1.x | Packs depend only on `PlatformTarget`/`Shot` types, which are graph-spec, not compiler-ABI, concerns |
| A Compiler built against Compiler ABI v1.0 continues to run against Creative Graph Spec v1.x (minor bumps) | Minor graph-spec bumps are additive only (`VERSIONING_POLICY.md`) |
| A `.nac` package exported at graph-spec v1.0 imports cleanly into a NAC installation running graph-spec v1.x for any x ≥ 0 | Forward compatibility within a major version is required; see `VERSIONING_POLICY.md` §`.nac` package versioning |
| A Plugin built against Plugin ABI v1.0 continues to receive events under Event Spec v1.x | Event taxonomy additions are minor-version, not breaking |

## Non-goals for extensibility (Phase 1)

- Hot-reloading a Pack/Plugin/Compiler without a NAC restart — not required in v1.0.
- Sandboxed/untrusted third-party packs — all packs in Phase 1 are first-party or
  explicitly vetted; no plugin marketplace security model exists yet.
- Cross-major-version compatibility (e.g. a v1.0 Pack against a hypothetical v2.0
  Compiler ABI) — major version bumps are explicitly allowed to break compatibility,
  see `VERSIONING_POLICY.md`.
