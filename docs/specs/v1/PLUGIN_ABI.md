# NAC Plugin ABI v1.0

**Status:** FROZEN (2026-07-03)
**Governed by:** `MANIFESTO.md` (plugins may not violate any of the 8 principles);
uses `EVENT_SPEC.md`'s `EventBus`.

## Purpose

A Plugin is the extension point for behavior that is neither a new generation tool
(that's a Pack, `PACK_ABI.md`) nor a new artifact type (that's a new Compiler,
`COMPILER_ABI.md`). Examples in scope for v1.0: a custom validation rule, a
third-party review-workflow integration, a telemetry exporter.

## Distinction from Packs and Compilers

| Extension type | Extends | Cannot do |
|---|---|---|
| Pack | A specific generation tool's prompt syntax | Cannot define a new node type or bypass the 8-stage compiler contract |
| Plugin | Cross-cutting behavior via events | Cannot write directly to any graph — must go through a Compiler or the Review workflow |
| Compiler | A new artifact type (new domain, e.g. future ComicCompiler) | N/A — this is the top-level extension point, requires a graph_spec-compatible node type set |

## Plugin contract

```
Plugin {
  plugin_id: str
  plugin_version: str          # semver, VERSIONING_POLICY.md
  abi_version: str              # "1.0", pins this document's version
  subscribed_events: list[str]   # EVENT_SPEC.md event_type patterns
  on_event(event: Event) -> None
}
```

## Hard constraints (enforced, not advisory)

1. A plugin's `on_event` handler MUST NOT call any Compiler's stage methods directly
   — it may only react by publishing new events (`EventBus.publish`) or by writing to
   the `ReviewGraph` via the Review workflow's public interface
   (`REPOSITORY_INTERFACES.md`).
2. A plugin MUST declare every event type it subscribes to at registration time —
   dynamic subscription changes at runtime are not supported in v1.0.
3. A plugin failure (unhandled exception in `on_event`) MUST NOT crash the publisher
   — the event bus catches and logs plugin exceptions, continuing delivery to other
   subscribers.

## Plugin discovery

Plugins are discovered under `engine/plugins/` the same way Packs are discovered
under `engine/packs/` (`PACK_ABI.md` §Pack discovery) — directory presence, not a
hardcoded registry list.
