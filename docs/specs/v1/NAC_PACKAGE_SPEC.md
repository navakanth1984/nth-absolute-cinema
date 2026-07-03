# NAC Package Specification v1.0 (`.nac` format)

**Status:** FROZEN (2026-07-03)
**Governed by:** `MANIFESTO.md` principle 4 (reproducibility via provenance).

## Purpose

A `.nac` file is a portable, self-describing archive of one NAC project, exportable
on one machine and importable on another with a different hardware profile, without
requiring the destination to already have the source machine's local models or cache.

## Container format

A `.nac` file is a `zip` archive (uncompressed manifest, compressed payload) with this
top-level layout:

```
movie.nac
├── manifest.json
├── graphs/
│   ├── knowledge_graph.json
│   ├── cinematic_graph.json
│   ├── asset_graph.json          (metadata only — see Asset handling below)
│   ├── production_graph.json
│   └── review_graph.json
├── genomes/
│   └── <genome_type>/<genome_id>.json     (all 9 genome types, CREATIVE_GRAPH_SPEC.md §4)
├── prompts/
│   └── <prompt_id>.json           (compiled Prompt IR, not raw text only)
├── provenance/
│   └── <artifact_id>.json         (Provenance blocks, CREATIVE_GRAPH_SPEC.md §9)
├── review_history/
│   └── <review_entry_id>.json
└── assets/
    ├── embedded/<content_hash>.<ext>      (small/source assets, embedded by hash)
    └── references.json                     (large renders: content_hash + relative
                                              path + regeneration provenance, NOT embedded
                                              unless embed_large_assets=true at export)
```

## Manifest schema

```
NacManifest {
  nac_format_version: str            # "1.0"
  graph_spec_version: str            # CREATIVE_GRAPH_SPEC.md version this project uses
  manifesto_version: str
  exported_at: str                   # ISO 8601
  exported_from_profile: str         # Compute Manager profile, COMPUTE_MANAGER_SPEC.md
  compiler_versions: dict[str, str]  # compiler_id -> compiler_version, ABI-checked
  pack_versions: dict[str, str]      # pack_id -> pack_version
  referenced_local_models: list[ModelReference]   # NOT the weights themselves
  embed_large_assets: bool
  content_hash_of_package: str       # sha256 of the archive contents (integrity check)
}

ModelReference {
  model_id: str
  model_version: str
  capability_tags: list[str]
  approx_size_mb: int
}
```

## Export rules

1. **Included, always:** all five graphs, all genomes, provenance, compiled prompts,
   review history, manifest.
2. **Included, content-addressed:** small/source assets (reference images, approved
   takes) — embedded by `content_hash` under `assets/embedded/`.
3. **Included by reference, embed optional:** large generated renders — always listed
   in `assets/references.json` with `content_hash` + regeneration provenance; embedded
   binary only if the export was run with `embed_large_assets=true`.
4. **Never included:** local model weights (`local_models/` tree), anything in the
   cache tier or `temp/` (`WORKSPACE_SPEC.md`), derived thumbnails/inference caches.

## Import rules (in order)

```
1. Verify manifest.nac_format_version and graph_spec_version are compatible with the
   importing NAC installation (VERSIONING_POLICY.md §`.nac` package versioning)
2. Restore all five graphs + genomes + provenance + review_history into projects/<new_id>/
3. Run Compute Manager hardware profiling on the destination machine
   (COMPUTE_MANAGER_SPEC.md) to select an execution profile
4. Diff manifest.referenced_local_models against installed models; install only the
   missing ones (COMPUTE_MANAGER_SPEC.md §Model Manager: on-demand installation)
5. For each entry in assets/references.json NOT embedded in the package: attempt
   regeneration from its Provenance block; if regeneration is not possible (e.g. a
   cloud model version no longer exists), mark the Asset node status="missing" rather
   than failing the whole import
```

An import that completes step 5 with some assets `status="missing"` is still a
successful import — Manifesto principle 4 requires reproducibility of the *creative
state* (graphs/genomes/provenance), not a guarantee that every historical cloud
render can always be re-fetched byte-identical.

## Integrity

`manifest.content_hash_of_package` is computed over the archive's file listing +
per-file hashes at export time and MUST be verified at the start of import (step 1,
before any graph data is trusted) — a `.nac` file that fails this check is rejected
outright, not partially imported.
