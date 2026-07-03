# NAC Compute Manager Specification v1.0

**Status:** FROZEN (2026-07-03)
**Governed by:** `MANIFESTO.md` principle 5 (offline-first, hardware-adaptive).

## Execution profiles

```
ComputeProfile = "Micro" | "Standard" | "Pro" | "Studio"
```

| Profile | Colloquial | Local scope |
|---|---|---|
| Micro | Laptop | Lightweight local LLMs, local TTS, prompt compilation, story generation, audio screenplay. Cloud video generation only when needed. |
| Standard | Gaming PC | Everything local except premium video. |
| Pro | Studio Workstation | Almost everything local. |
| Studio | Cloud | Heavy rendering, distributed generation, team collaboration. |

## Profiling contract

```
HardwareProfile {
  cpu_cores: int
  ram_gb: float
  gpu_name: str | None
  vram_gb: float | None
  storage_free_gb: float
  storage_kind: str            # "ssd" | "hdd" | "network"
  installed_models: list[ModelReference]     # NAC_PACKAGE_SPEC.md ModelReference
}

ComputeManager {
  profile_hardware() -> HardwareProfile
  select_profile(hw: HardwareProfile) -> ComputeProfile
  current_profile() -> ComputeProfile
  reprofile() -> ComputeProfile        # re-run detection; used on project relocation
}
```

`select_profile` is a pure function of `HardwareProfile` — deterministic thresholds
(exact GB/VRAM cutoffs are an implementation detail of Sprint 1, not fixed by this
spec, but the function signature and the four-value output enum are frozen here).

## Model Manager: on-demand installation

```
ModelManager {
  is_installed(model_id: str) -> bool
  install(model_id: str) -> ModelReference       # emits model.install.completed (EVENT_SPEC.md)
  resolve_for_capability(capability_tag: str, profile: ComputeProfile) -> ModelReference | None
}
```

**Hard rule:** `ModelManager` never installs a model that was not explicitly
requested by a compiler's capability lookup (`resolve_for_capability`). There is no
"install everything" path in v1.0 — a fresh `Micro`-profile project may run correctly
having installed only 1-2 small models.

## Model package manifest

Each installable model under `local_models/` has its own manifest:

```
ModelPackageManifest {
  model_id: str
  model_version: str
  approx_size_mb: int
  min_vram_gb: float | None
  capability_tags: list[str]           # e.g. ["narration", "tts", "local"]
  compatible_profiles: list[ComputeProfile]
}
```

## Relationship to Model Manager routing (Tier 0-4)

The existing Tier 0-4 routing concept (Python deterministic → local LLM → local image
→ local audio → cloud) is unchanged by this spec — `ComputeManager.current_profile()`
constrains *which* tiers are actually reachable on this machine; it does not replace
the tier concept itself.

## Relationship to `.nac` import

On `.nac` import (`NAC_PACKAGE_SPEC.md`), step 3 calls `profile_hardware()` +
`select_profile()` fresh on the destination machine (never trusts the source
manifest's `exported_from_profile` as authoritative for the destination), and step 4
diffs `manifest.referenced_local_models` against `is_installed()` results, calling
`install()` only for the gap.
