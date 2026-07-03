# NAC Creative Compiler ABI v1.0

**Status:** FROZEN (2026-07-03)
**Governed by:** `MANIFESTO.md` principles 2, 3, 4, 6, 7. Uses types from
`CREATIVE_GRAPH_SPEC.md` §8 (`ValidationResult`) and §9 (`Provenance`).

## Compiler contract (the 8-stage pipeline)

Every compiler (ScreenplayCompiler, StoryBibleCompiler, NovelCompiler, AudioCompiler,
DialogueCompiler, NarrationCompiler, PromptCompiler, StoryboardCompiler,
MotionPosterCompiler, TeaserCompiler, TrailerCompiler) implements exactly these 8
stages, in this order, with no stage skipped:

```
1. Input Schema   — declares which CREATIVE_GRAPH_SPEC.md node types it reads
2. Validation     — runs the four-layer contract (CREATIVE_GRAPH_SPEC.md §8);
                     halts on any failing layer
3. Planning       — produces an Estimate (CREATIVE_GRAPH_SPEC.md §6) BEFORE generation
4. Generation     — calls Model Manager (COMPUTE_MANAGER_SPEC.md) for the actual work
5. Measurement    — measures the real output (duration, token count, actual cost) —
                     never trusts the Planning-stage estimate as the final number
6. Repair         — if Measurement finds a fixable defect, re-invoke Generation with
                     corrective input; bounded retry count (compiler-specific, but
                     MUST be finite and logged)
7. Review         — writes a ReviewEntry (CREATIVE_GRAPH_SPEC.md §7) with
                     stage="ai_self_review"; does not proceed to Export without a
                     corresponding stage="human_review" ReviewEntry with
                     verdict="approved"
8. Export         — writes the final Asset/Prompt node with a populated Provenance
                     block (CREATIVE_GRAPH_SPEC.md §9)
```

No compiler may write an `Asset` or `Prompt` node outside of stage 8. No compiler may
skip stage 3 (Planning/Estimate) — this is what makes Manifesto principle 7 (economic
efficiency as a first-class objective) enforceable rather than aspirational.

## Estimation contract

Stage 3 (Planning) MUST produce exactly one `Estimate` node (CREATIVE_GRAPH_SPEC.md
§6) per `Job`. The `confidence` field is required — a compiler with no historical
data for a given operation MUST report a low confidence value rather than omitting
the field or hardcoding `1.0`.

## Provenance contract

Stage 8 (Export) MUST populate every field of `Provenance` (CREATIVE_GRAPH_SPEC.md
§9). `compiler_version` MUST be the exact semver of the compiler that ran (see
`VERSIONING_POLICY.md`) — not the ABI version. A missing or null Provenance field on
an exported Asset/Prompt is a contract violation, not a warning.

## Review contract

A ReviewEntry with `stage="ai_self_review"` is REQUIRED before any
`stage="human_review"` entry may be written for the same artifact — self-review runs
first and its result (even if `verdict="rejected"`) is retained, not overwritten, when
human review later approves.

## Failure semantics

If Validation (stage 2) fails, the compiler MUST NOT proceed past stage 2 and MUST
return a `ValidationResult` list (CREATIVE_GRAPH_SPEC.md §8) — no partial artifact is
written. If Repair (stage 6) exhausts its bounded retry count without a passing
Measurement, the compiler MUST write a `Job` with `status="failed"`
(CREATIVE_GRAPH_SPEC.md §6) rather than silently exporting a defective artifact.

## Compiler registration

Every compiler declares:
```
CompilerDeclaration {
  compiler_id: str            # e.g. "screenplay_compiler"
  compiler_version: str       # semver
  abi_version: str            # this document's version, "1.0"
  consumes_node_types: list[str]   # CREATIVE_GRAPH_SPEC.md node type names
  produces_node_types: list[str]
}
```

`abi_version` pins which version of this document the compiler was written against —
see `VERSIONING_POLICY.md` §Creative Compiler ABI versioning for the compatibility rule.
