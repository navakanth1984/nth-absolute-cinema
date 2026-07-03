# NAC Event Specification v1.0

**Status:** FROZEN (2026-07-03)
**Governed by:** `COMPILER_ABI.md` (8-stage pipeline emits these events).

## Purpose

The event bus is how one compiler's output triggers another compiler's input without
direct coupling — e.g. "screenplay compiled" triggering the Prompt Compiler. Every
cross-module reaction in NAC goes through this event system; no module calls another
module's compiler directly (see `MODULE_BOUNDARIES.md`).

## Event envelope

Every event on the bus has this exact shape:

```
Event {
  event_id: UUID
  event_type: str            # dot-namespaced, see taxonomy below
  occurred_at: str            # ISO 8601
  project_id: UUID
  source: str                  # compiler_id, pack_id, or "system"
  payload: dict                 # event_type-specific, schemas below
  graph_snapshot_version: str    # KnowledgeGraph/CinematicGraph version at emit time
}
```

## Event taxonomy (v1.0 — closed set; extending requires a VERSIONING_POLICY.md minor bump)

```
graph.knowledge.updated        { changed_node_ids: list[UUID] }
graph.cinematic.updated        { changed_node_ids: list[UUID] }
compiler.stage.entered         { compiler_id, job_id: UUID, stage: str }   # one of the 8 stages, COMPILER_ABI.md
compiler.stage.completed       { compiler_id, job_id: UUID, stage: str, duration_ms: int }
compiler.job.failed            { compiler_id, job_id: UUID, stage: str, reason: str }
compiler.artifact.exported     { compiler_id, job_id: UUID, artifact_id: UUID, artifact_kind: str }
review.entry.created           { review_entry_id: UUID, artifact_id: UUID, stage: str, verdict: str }
production.estimate.created    { estimate_id: UUID, job_id: UUID }
nac.export.completed           { package_path: RelativePath, manifest_hash: str }
nac.import.completed           { source_manifest_hash: str, missing_asset_ids: list[UUID] }
compute.profile.selected       { profile: str, reason: str }             # COMPUTE_MANAGER_SPEC.md
model.install.completed        { model_id: str, model_version: str }
```

## Subscription contract

```
EventBus {
  publish(event: Event) -> None
  subscribe(event_type_pattern: str, handler: Callable[[Event], None]) -> SubscriptionHandle
  unsubscribe(handle: SubscriptionHandle) -> None
}
```

`event_type_pattern` supports a single trailing wildcard (`"compiler.stage.*"`
matches both `entered` and `completed`) — no other glob syntax is supported in v1.0.

## Ordering and delivery guarantees

- Events for a single `project_id` are delivered to subscribers in emission order.
- Delivery is at-least-once, not exactly-once — handlers MUST be idempotent w.r.t.
  `event_id` (dedupe on `event_id` if a handler's side effect isn't naturally
  idempotent).
- The event bus is in-process for Phase 1 (no distributed queue) — this MAY change in
  a later phase for the Studio (Cloud) Compute Manager profile, but that change would
  be additive (a different `EventBus` implementation satisfying the same interface),
  not a change to this spec.
