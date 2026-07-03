# NAC Pack ABI v1.0

**Status:** FROZEN (2026-07-03)
**Governed by:** `MANIFESTO.md` principle 5 (offline-first). Uses types from
`CREATIVE_GRAPH_SPEC.md` §3.1 (`PlatformTarget`), §5 (`Prompt`).

## Purpose

A NAC Pack is the sole extension mechanism for adding a generation tool (Google Flow,
Higgsfield, OpenArt, Flux, ComfyUI, ...) to the Prompt Compiler. `COMPILER_ABI.md`'s
Prompt Compiler never hardcodes a tool integration — it always calls through a Pack.

## Required Pack components

Every pack under `engine/packs/<pack_id>/` MUST provide exactly these five
components:

> **Note on component naming:** the design doc (§7) lists six pack sub-components
> (`parser, prompt_compiler, validator, capability_matrix, limits, templates,
> examples`). This ABI consolidates `limits` into `CapabilityMatrix` (the `max_*`
> fields) and `examples` into `Templates` (reusable fragments include worked
> examples) — five components, not seven, with no capability lost.

```
Parser              — parses a CinematicGraph Shot + genome refs into the pack's
                       internal prompt representation
PromptCompiler       — compiles that representation into the tool's native prompt
                       syntax, ONE output per PlatformTarget on the Shot (no crop —
                       see CREATIVE_GRAPH_SPEC.md §3.1)
Validator            — checks the compiled prompt against CapabilityMatrix limits
                       (below) BEFORE it is sent to Generation
CapabilityMatrix     — static declaration of the tool's strengths/weaknesses/limits
Templates            — reusable prompt fragments (camera syntax, motion syntax,
                       negative-prompt boilerplate) specific to this tool
```

## CapabilityMatrix schema

```
CapabilityMatrix {
  pack_id: str
  pack_version: str            # semver, see VERSIONING_POLICY.md
  supported_platforms: list[PlatformTarget]
  max_prompt_tokens: int
  max_duration_s: float | None
  supported_aspect_ratios: list[str]
  supports_negative_prompt: bool
  supports_seed: bool
  known_limitations: list[str]
  requires_cloud: bool          # True for e.g. Google Flow; False for local packs
}
```

`Validator` MUST reject (Technical validation layer, `CREATIVE_GRAPH_SPEC.md` §8) any
compiled prompt exceeding `max_prompt_tokens` or requesting an unsupported
`aspect_ratio` — this is where the four-layer validation contract's Technical layer is
actually implemented for prompt generation.

## Capability Registry

```
CapabilityRegistry {
  register(pack: PackDeclaration) -> None
  resolve(platform_target: PlatformTarget, requires_cloud: bool | None) -> list[PackDeclaration]
}

PackDeclaration {
  pack_id: str
  pack_version: str
  abi_version: str              # "1.0", pins PACK_ABI.md version
  capability_matrix: CapabilityMatrix
}
```

`PromptCompiler` (in `COMPILER_ABI.md`'s sense) asks `CapabilityRegistry.resolve()`
for candidate packs given a `Shot`'s `target_platforms`; it never imports a specific
pack module directly. This is the mechanism that makes "new tool support = new pack,
zero core changes" (design doc §7) an architectural guarantee rather than a
convention.

## Pack discovery

Packs are discovered by directory presence under `engine/packs/`, not by a central
hardcoded list. A pack missing any of the five required components (above) MUST fail
`CapabilityRegistry.register()` at startup rather than registering partially.

## Versioning

See `VERSIONING_POLICY.md` §Pack versioning. `pack_version` is recorded in every
`Prompt` node's `Provenance.pack_version` (`CREATIVE_GRAPH_SPEC.md` §9) and in every
`.nac` manifest (`NAC_PACKAGE_SPEC.md`).
