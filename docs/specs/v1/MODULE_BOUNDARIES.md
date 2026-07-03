# NAC Module Dependency Diagram & Import Boundaries v1.0

**Status:** FROZEN (2026-07-03)

## Diagram

```
                        ┌───────────────┐
                        │  engine.api   │  (only door to dashboard/CLI)
                        └───────┬───────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                  ▼
      ┌───────────────┐ ┌───────────────┐ ┌────────────────┐
      │engine.compilers│ │engine.review  │ │engine.production│
      └───────┬────────┘ └───────┬───────┘ └────────┬────────┘
              │                  │                   │
              ▼                  ▼                   ▼
      ┌────────────────────────────────────────────────────┐
      │        engine.knowledge / engine.cinematic /         │
      │        engine.assets  (the five graphs)               │
      └───────────────────────┬──────────────────────────────┘
                               │
                               ▼
                      ┌────────────────┐
                      │ engine.storage │
                      └───────┬────────┘
                               │
                               ▼
                      ┌────────────────┐
                      │ engine.kernel  │  (paths, Compiler base class, EventBus)
                      └────────────────┘

  engine.packs        → used ONLY by engine.compilers (PromptCompiler), never by
                          engine.knowledge/cinematic/assets directly
  engine.plugins       → used ONLY via engine.kernel.EventBus subscriptions
  engine.model_manager  → used by engine.compilers (Generation stage) AND
                            engine.compute_manager
  engine.compute_manager → used by engine.model_manager, engine.portability
  engine.portability      → used by engine.api only (export/import is a top-level
                              operation, not something a compiler triggers)
```

## Allowed import rules (enforced by lint in Sprint 1, declared here)

1. `engine.kernel` imports nothing else under `engine/` — it is the dependency floor.
2. `engine.storage` may import `engine.kernel` only.
3. `engine.knowledge`, `engine.cinematic`, `engine.assets`, `engine.production`,
   `engine.review` may import `engine.kernel` and `engine.storage` only — never each
   other directly (cross-graph reactions go through `engine.kernel.EventBus`, per
   `EVENT_SPEC.md`).
4. `engine.compilers.*` may import `engine.kernel`, `engine.storage`, the five graph
   modules (read/write via their repository interfaces, `REPOSITORY_INTERFACES.md`),
   and `engine.model_manager`. A compiler MAY import `engine.packs` only if it is the
   Prompt Compiler specifically.
5. `engine.packs.*` may import `engine.kernel` (for `PlatformTarget`-adjacent types)
   only — a pack MUST NOT import `engine.compilers`, `engine.storage`, or any graph
   module directly.
6. `engine.plugins.*` may import `engine.kernel.EventBus` and
   `REPOSITORY_INTERFACES.md`'s `ReviewRepository` only — no direct graph writes
   (`PLUGIN_ABI.md` hard constraint 1).
7. `engine.compute_manager` and `engine.model_manager` may import `engine.kernel`
   only.
8. `engine.portability` may import `engine.kernel`, `engine.storage`, all five graph
   modules (read-only for export, write for import), `engine.compute_manager`, and
   `engine.model_manager`.
9. `engine.api` may import anything under `engine/` — it is the only module allowed
   to. `dashboard/` (Node/React, later sprint) may only call `engine.api` over HTTP —
   it never imports Python modules directly.

Any import not covered by rules 1-9 is disallowed by default — a new module added in
a later sprint must have its import rule added to this list before it ships.
