# Sprint 3A.5 — Phase 1 Verification Findings

Date: 2026-07-04
Method: live server (`nac-director-studio`, port 8421) driven via browser automation
(DOM/accessibility-tree inspection + `preview_eval`, not screenshots — see note below).
Branch: `feat/storage-manager`. Server started without `--reload`; restarted once after
backend fixes.

## Tooling note

The `preview_screenshot` tool returned images that visually contradicted the live DOM
(reported a collapsed ~280x140px layout at a 1400x900 viewport). Cross-checked with
`preview_eval`/`preview_inspect`, which showed correct full-width grid layout
(`220px / 1fr / 260px` columns, full viewport). Treated as a screenshot-tool artifact,
not a product bug — verification for this pass relied on `preview_snapshot` /
`preview_eval` / `preview_network`, not screenshots.

## Bugs found and fixed

1. **`/status` endpoint missing `idea_text` / `target_runtime_minutes`.**
   `engine/storage/knowledge_repo.py: get_status()` never returned these fields, even
   though the previous (uncommitted) Sprint 3A frontend rewrite (`renderRightPanel`,
   `renderIdeaWorkspace` in `dashboard/static/app.js`) assumes them. This threw an
   uncaught `TypeError` inside `refreshProject()` on every project open, which — because
   the throw happened mid-function — silently broke **two things per initial page load**:
   the "Production Info" right panel (stayed empty) and the initial Production Timeline
   render (masked once you switched stages, since `selectStage` calls `renderTimeline()`
   independently). The Concept & Pitch workspace threw the same error whenever opened
   directly. **Fixed** by adding both fields to the status dict (data already existed in
   the `story` row, just wasn't exposed). Verified via reload: right panel renders,
   Concept & Pitch workspace renders, dependent workspaces unaffected. All 125 tests pass.

2. **Aspect ratio selection leaked across projects.** `state.aspectRatio` was set once
   from `localStorage` on first use and never reset when switching to a *different*
   project (`openProject()` didn't clear it). Opening Project B right after setting
   Project A's ratio to 9:16 showed 9:16 as the (wrong) selected value in Project B's
   dropdown, even for a brand-new project with no stored preference. **Fixed** by
   resetting `state.aspectRatio = null` in `openProject()`. Verified: fresh project now
   correctly shows 16:9 default; switching between two live projects (Temple of Varuna =
   9:16, lighthouse project = 16:9) now shows the correct value for each, independently.

Both fixes are two-line, root-cause, additive changes; no test or contract changes were
needed beyond the fix itself. `py -3.12 -m pytest -q` → 125 passed both before and after.

## Confirmed working (unassisted, via live interaction)

- Project creation (idea + runtime → new project, lands in studio view).
- Project switching between two existing projects (state correctly isolated post-fix).
- Demo project load.
- Department-grouped left nav (Development / Pre-Production / Production Assets /
  Infrastructure / Supervision) renders and is clickable.
- Story Bible workspace: content render, review controls (Approve/Needs Revision/
  Reject), decision history section.
- Screenplay content present via same generative-stage workspace path (verified via API
  response; not independently re-clicked, but shares the fixed code path with Story
  Bible).
- Audio generation: triggered "Compile Stage" on a project with no audio yet → real
  pyttsx3 TTS ran (`duration_s: 5.016`, `model: pyttsx3`), execution metrics rendered.
- Motion Poster Prompt generation: triggered compile → real (mock-provider) output
  rendered, framing preview crop label reflects the project's aspect ratio.
- Storage workspace: lists registered providers (local/external/azure/google) with
  capability matrices; `external` and cloud providers show `UNHEALTHY` (plausible given
  no cloud creds/mount configured in this environment — not verified as a bug).
- Snapshots workspace: Create Snapshot → real snapshot with Merkle master hash appears;
  Verify Integrity → real `INTEGRITY OK` verdict. Inspect Manifest not clicked this pass.
  Restore correctly shows as disabled ("RestoreManager planned for next milestone") —
  matches the project's actual stated scope, not a bug.
- Packages workspace: Create .nac Package → real package appears with path on disk,
  Manifest/Browse Files links present (not clicked this pass).
- Diagnostics workspace: real system info (Python version, disk free, GPU, LLM provider
  reachability/fallback chain, active storage, snapshot count, per-project graph
  validation health) — no placeholder data observed.
- Creative Graph: canvas element renders at reasonable size (750x350), no console
  errors on render.
- Aspect ratio persistence: selecting a ratio writes to
  `localStorage['nac_project_<id>_aspect_ratio']`; survives a full page reload for the
  same project (post-fix); correctly isolated per-project (post-fix).
- Command palette: Ctrl+K opens it (verified via synthetic KeyboardEvent), Escape closes
  it, input filters the command list.

## Confirmed cosmetic-only gap (documented, not fixed — matches stated scope)

- **Aspect ratio does not reach the backend prompt compiler.** The Cinematography
  workspace's "Framing Preview" label correctly shows the selected ratio (e.g. 9:16),
  but the actual generated Motion Poster Prompt content still hardcodes
  `aspect_ratio: 16:9` regardless of selection. This matches Sprint 2A's own documented
  limitation ("Aspect Ratios ... not implemented in this build — the NAC engine has no
  fields for them yet"). The Sprint 3A UI work makes the ratio *look* first-class
  (selector, persistence, framing preview) but it is still frontend/localStorage-only —
  it does not flow into `prompt_compiler`. Not fixed in this pass; flagging as a Phase
  2/3 decision point: either wire it through the compiler input, or make the UI copy
  honest about it being a preview-only setting until the compiler supports it.

## Not yet exercised this pass (time-boxed out, flagging for later)

- Inspect Manifest (snapshots) and Manifest/Browse Files (packages) — buttons present,
  not clicked.
- Full keyboard-shortcut set beyond Ctrl+K/Escape (if more are defined in `COMMANDS`).
- Empty-state / loading-state / error-state visuals under adverse conditions (e.g. LLM
  provider failure, no snapshots yet — the "no snapshots yet" empty state was seen
  incidentally and read fine).
- Import asset flow, export/package-download flow end-to-end.
