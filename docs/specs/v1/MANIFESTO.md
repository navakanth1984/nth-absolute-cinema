# NAC Creative Compiler Manifesto v1.0

**Status:** FROZEN (2026-07-03)

Philosophy that every NAC compiler, pack, and future domain (novel, comic, game,
podcast, course) must obey. This document is stable across implementation churn — it
does not change when `CREATIVE_GRAPH_SPEC.md` or `COMPILER_ABI.md` evolve to v1.1+.

## The eight principles

1. **The Creative Knowledge Graph is the single source of truth.** No compiler, no
   artifact, no cache holds authoritative state that isn't derivable from the five
   graphs defined in `CREATIVE_GRAPH_SPEC.md`.
2. **Every artifact is compiled, never authored in isolation.** A screenplay, a
   prompt, an audio file — none of these are hand-edited independent of the graph
   that produced them. Edits go back through the graph and recompile.
3. **Humans direct; AI proposes.** Every compiler's output is a proposal subject to
   the review workflow (`CREATIVE_GRAPH_SPEC.md` §Review Graph); no artifact reaches
   "accepted" state without passing through Human Review.
4. **Outputs must be reproducible through provenance.** Every artifact carries enough
   metadata (`COMPILER_ABI.md` §Provenance) to regenerate it exactly, or to explain
   exactly why it differs on regeneration.
5. **Offline-first by default; cloud only when it adds measurable value.** Every
   capability must have a local execution path (`COMPUTE_MANAGER_SPEC.md`); cloud is
   an enhancement tier, never a requirement to produce a minimum-viable artifact.
6. **Quality and consistency outweigh generation speed.** Compilers are permitted to
   retry, validate, and repair (`COMPILER_ABI.md` §Compiler Contract) rather than
   emit a first-pass result.
7. **Economic efficiency is a first-class optimization objective.** Every compiler
   reports a cost/time/resource estimate before generation (`COMPILER_ABI.md`
   §Estimation) — this is not optional instrumentation, it is a contract requirement.
8. **Every creative decision is traceable back to the project state that produced
   it.** Provenance (principle 4) plus the Review Graph together answer "why does
   this artifact exist" for any artifact, at any time.

## Scope

This Manifesto governs NAC's Phase 1 domain (film) and any future domain built on the
same Creative Compiler Framework (novel, comic, game, podcast, course — see
`docs/superpowers/specs/2026-07-03-nth-absolute-cinema-design.md` §1). It does not
govern the Nth Absolute Cinema Studio desktop application's UI/UX decisions, which may
change freely as long as they do not violate these eight principles.

## Amendment process

A change to this document requires: (1) a written rationale for which principle is
being added/removed/reworded and why, (2) an audit of every existing spec document in
`docs/specs/v1/` for compliance with the proposed change, (3) explicit user approval.
This mirrors CRP's RFC discipline (`docs/vision/TITAN.md`) without importing CRP's
RFC tooling — NAC and CRP remain separate projects.
