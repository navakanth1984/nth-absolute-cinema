// NAC Director Studio - Sprint 2A. Talks only to /api/* routes, which are thin
// wrappers over nac.Studio. No client-side invention of unsupported fields.

const state = { projectId: null, activeStage: "story", status: null, project: null };

const STAGES = [
  { id: "idea", label: "Idea", real: true },
  { id: "story", label: "Story Bible", real: true },
  { id: "screenplay", label: "Screenplay", real: true },
  { id: "audio", label: "Audio", real: true },
  { id: "prompt", label: "Motion Poster", real: true },
  { id: "export", label: "Export", real: true },
  { id: "reviews", label: "Reviews", real: true },
  { id: "assets", label: "Assets", real: true },
  { id: "settings", label: "Settings", real: true },
  { id: "characters", label: "Characters (Coming Soon)", real: false },
  { id: "scenes", label: "Scenes (Coming Soon)", real: false },
  { id: "shots", label: "Shots (Coming Soon)", real: false },
  { id: "trailer", label: "Trailer (Coming Soon)", real: false },
  { id: "movie", label: "Movie (Coming Soon)", real: false },
];

const TIMELINE_STAGES = ["idea", "story", "screenplay", "audio", "prompt", "export"];

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `${res.status} ${res.statusText}`);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res;
}

function toast(msg, isError = false) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast" + (isError ? " error" : "");
  t.classList.remove("hidden");
  clearTimeout(toast._hideTimer);
  toast._hideTimer = setTimeout(() => t.classList.add("hidden"), isError ? 12000 : 3500);
}

// ---------- Home view ----------

async function renderHome() {
  document.getElementById("studio-view").classList.add("hidden");
  document.getElementById("home-view").classList.remove("hidden");
  const list = document.getElementById("project-list");
  list.innerHTML = "<p>Loading...</p>";
  try {
    const projects = await api("/api/projects");
    if (!projects.length) {
      list.innerHTML = "<p style='color:var(--text-dim)'>No projects yet.</p>";
      return;
    }
    list.innerHTML = "";
    for (const p of projects) {
      const card = document.createElement("div");
      card.className = "project-card";
      const doneCount = ["story_bible", "screenplay", "audio", "motion_poster_prompt"]
        .filter((k) => p[k]).length;
      card.innerHTML = `
        <div class="idea">${escapeHtml(p.idea_text)}</div>
        <div class="meta">
          <span>${p.target_runtime_minutes} min target</span>
          <span>${doneCount}/4 stages</span>
          <span>${p.created_at || ""}</span>
        </div>`;
      card.onclick = () => openProject(p.id);
      list.appendChild(card);
    }
  } catch (e) {
    list.innerHTML = `<p style="color:var(--red)">Failed to load projects: ${e.message}</p>`;
  }
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s ?? "";
  return d.innerHTML;
}

// ---------- New project dialog ----------

document.getElementById("new-project-btn").onclick = () => {
  document.getElementById("np-idea").value = "";
  document.getElementById("np-runtime").value = "15";
  document.getElementById("new-project-dialog").classList.remove("hidden");
};
document.getElementById("np-cancel").onclick = () =>
  document.getElementById("new-project-dialog").classList.add("hidden");
document.getElementById("np-create").onclick = async () => {
  const idea_text = document.getElementById("np-idea").value.trim();
  const target_runtime_minutes = parseInt(document.getElementById("np-runtime").value, 10) || 15;
  if (!idea_text) { toast("Idea is required", true); return; }
  try {
    const { id } = await api("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idea_text, target_runtime_minutes }),
    });
    document.getElementById("new-project-dialog").classList.add("hidden");
    openProject(id);
  } catch (e) {
    toast(e.message, true);
  }
};

// ---------- Project workspace ----------

async function openProject(id) {
  state.projectId = id;
  document.getElementById("home-view").classList.add("hidden");
  document.getElementById("studio-view").classList.remove("hidden");
  await refreshProject();
  selectStage("story");
}

document.getElementById("back-to-home").onclick = () => {
  state.projectId = null;
  renderHome();
};

async function refreshProject() {
  const [status, provider] = await Promise.all([
    api(`/api/projects/${state.projectId}/status`),
    api("/api/provider").catch(() => ({ llm_provider: "unknown" })),
  ]);
  state.status = status;
  state.provider = provider;
  renderNav();
  renderRightPanel();
  renderTimeline();
}

function statusFor(stageId) {
  if (!state.status) return "waiting";
  const map = { story: "story_bible", screenplay: "screenplay", audio: "audio", prompt: "motion_poster_prompt" };
  if (stageId === "idea") return "done";
  const key = map[stageId];
  if (!key) return "n/a";
  return state.status[key] ? "done" : "waiting";
}

function stageUnlocked(stageId) {
  const order = ["idea", "story", "screenplay", "audio", "prompt"];
  const idx = order.indexOf(stageId);
  if (idx <= 0) return true;
  const prevKey = { story: "idea", screenplay: "story_bible", audio: "screenplay", prompt: "audio" }[stageId];
  if (stageId === "screenplay") return !!state.status.story_bible;
  if (stageId === "audio") return !!state.status.screenplay;
  if (stageId === "prompt") return !!state.status.audio;
  return true;
}

function renderNav() {
  const nav = document.getElementById("nav-list");
  nav.innerHTML = "";
  for (const s of STAGES) {
    const li = document.createElement("li");
    li.className = "nav-item" + (!s.real ? " disabled" : "") + (state.activeStage === s.id ? " active" : "");
    const st = s.real ? statusFor(s.id) : null;
    const dot = st && st !== "n/a" ? `<span class="status-dot ${st}"></span>` : "";
    li.innerHTML = `<span>${s.label}</span>${dot}`;
    if (s.real) li.onclick = () => selectStage(s.id);
    nav.appendChild(li);
  }
}

function renderRightPanel() {
  const s = state.status;
  const doneCount = ["story_bible", "screenplay", "audio", "motion_poster_prompt"].filter((k) => s[k]).length;
  const pct = Math.round((doneCount / 4) * 100);
  const el = document.getElementById("production-info");
  el.innerHTML = `
    <div class="progress-bar"><div class="progress-bar-fill" style="width:${pct}%"></div></div>
    <div class="info-row"><span>Progress</span><span class="v">${doneCount}/4 stages (${pct}%)</span></div>
    <div class="info-row"><span>LLM Provider</span><span class="v">${state.provider.llm_provider}</span></div>
    <div class="info-row"><span>Assets Imported</span><span class="v">${s.asset_count}</span></div>
    <div class="info-row"><span>Reviews Recorded</span><span class="v">${s.review_count}</span></div>
    <p style="font-size:11px;color:var(--text-dim);margin-top:14px;line-height:1.5;">
      Estimated Runtime/Pages/Tokens, GPU Usage, Execution Mode, and Credits are not
      shown here - the engine does not compute or store them yet.
    </p>`;
}

function renderTimeline() {
  const s = state.status;
  const map = { idea: true, story: s.story_bible, screenplay: s.screenplay, audio: s.audio, prompt: s.motion_poster_prompt, export: false };
  const el = document.getElementById("timeline");
  el.innerHTML = "";
  for (const id of TIMELINE_STAGES) {
    const label = STAGES.find((x) => x.id === id).label;
    const done = map[id];
    const div = document.createElement("div");
    div.className = "tl-stage";
    div.innerHTML = `<div class="label">${label}</div>
      <div class="tl-bar"><div class="tl-bar-fill ${done ? "" : "empty"}" style="width:${done ? 100 : 0}%"></div></div>`;
    el.appendChild(div);
  }
}

async function selectStage(stageId) {
  state.activeStage = stageId;
  renderNav();
  const ws = document.getElementById("stage-workspace");
  ws.innerHTML = "<p>Loading...</p>";

  if (stageId === "idea") return renderIdeaWorkspace();
  if (stageId === "export") return renderExportWorkspace();
  if (stageId === "reviews") return renderReviewsWorkspace();
  if (stageId === "assets") return renderAssetsWorkspace();
  if (stageId === "settings") return renderSettingsWorkspace();
  return renderGenerativeStageWorkspace(stageId);
}

function renderIdeaWorkspace() {
  const ws = document.getElementById("stage-workspace");
  ws.innerHTML = `<h2>Idea</h2><div class="stage-content">${escapeHtml(state.status.idea ? "(idea recorded - see project list for text)" : "")}</div>`;
}

const STAGE_META = {
  story: { label: "Story Bible", contentKey: "story" },
  screenplay: { label: "Screenplay", contentKey: "screenplay" },
  audio: { label: "Audio Screenplay", contentKey: null },
  prompt: { label: "Motion Poster Prompt", contentKey: "prompt" },
};

async function renderGenerativeStageWorkspace(stageId) {
  const meta = STAGE_META[stageId];
  const unlocked = stageUnlocked(stageId);
  const done = statusFor(stageId) === "done";
  const ws = document.getElementById("stage-workspace");

  const [content, reviews, metrics] = await Promise.all([
    api(`/api/projects/${state.projectId}/content`),
    api(`/api/projects/${state.projectId}/reviews`),
    api(`/api/projects/${state.projectId}/metrics`),
  ]);
  const stageReviews = reviews.filter((r) => r.stage === stageId);
  const stageMetrics = metrics.find((m) => m.compiler && m.compiler.toLowerCase().includes(stageId));

  ws.innerHTML = `
    <h2>${meta.label}</h2>
    <div class="stage-actions">
      <button id="gen-btn" class="btn btn-primary" ${unlocked ? "" : "disabled"}>${done ? "Regenerate" : "Generate"}</button>
      ${!unlocked ? '<span style="color:var(--text-dim);font-size:12px;align-self:center;">Locked - approve the previous stage first</span>' : ""}
    </div>
    ${stageId === "audio" ? renderAudioPlayer() : `<div class="stage-content" id="content-box">${escapeHtml(content[meta.contentKey] || "(not generated yet)")}</div>`}
    ${stageMetrics ? `<div class="section-title">Metrics</div><div class="stage-content">${escapeHtml(JSON.stringify(stageMetrics, null, 2))}</div>` : ""}
    <div class="section-title">Review</div>
    <div class="review-controls">
      <button class="btn" data-verdict="approved">Approve</button>
      <button class="btn" data-verdict="needs_revision">Needs Changes</button>
      <button class="btn" data-verdict="rejected">Reject</button>
      <input id="review-comment" placeholder="Comment (optional)">
    </div>
    <div class="section-title">History</div>
    <div id="history-list">${stageReviews.length ? stageReviews.map(historyItem).join("") : '<p style="color:var(--text-dim);font-size:12px;">No reviews yet.</p>'}</div>
  `;

  document.getElementById("gen-btn").onclick = async () => {
    document.getElementById("gen-btn").disabled = true;
    document.getElementById("gen-btn").textContent = "Generating...";
    try {
      await api(`/api/projects/${state.projectId}/generate/${stageId}`, { method: "POST" });
      toast(`${meta.label} generated`);
      await refreshProject();
      selectStage(stageId);
    } catch (e) {
      toast(e.message, true);
      const btn = document.getElementById("gen-btn");
      btn.disabled = false;
      btn.textContent = done ? "Regenerate" : "Generate";
    }
  };

  ws.querySelectorAll("[data-verdict]").forEach((btn) => {
    btn.onclick = async () => {
      const verdict = btn.dataset.verdict;
      const comment = document.getElementById("review-comment").value || null;
      try {
        await api(`/api/projects/${state.projectId}/review`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ stage: stageId, verdict, comment }),
        });
        toast(`Recorded: ${stageId} -> ${verdict}`);
        selectStage(stageId);
      } catch (e) {
        toast(e.message, true);
      }
    };
  });
}

function historyItem(r) {
  return `<div class="history-item verdict-${r.verdict}">
    <strong>${r.verdict}</strong> - ${r.created_at || ""}
    ${r.comment ? `<div>${escapeHtml(r.comment)}</div>` : ""}
  </div>`;
}

function renderAudioPlayer() {
  return `<audio controls style="width:100%" src="/api/projects/${state.projectId}/audio"></audio>`;
}

function renderExportWorkspace() {
  const ws = document.getElementById("stage-workspace");
  ws.innerHTML = `
    <h2>Export</h2>
    <p style="color:var(--text-dim);font-size:13px;">Exports whatever stages are populated right now into a Production Package.</p>
    <div class="stage-actions"><button id="export-btn" class="btn btn-primary">Export Project</button></div>
    <div id="export-result"></div>`;
  document.getElementById("export-btn").onclick = async () => {
    try {
      const { path } = await api(`/api/projects/${state.projectId}/export`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
      });
      document.getElementById("export-result").innerHTML = `<div class="stage-content">Exported to: ${escapeHtml(path)}</div>`;
      toast("Export complete");
    } catch (e) {
      toast(e.message, true);
    }
  };
}

async function renderReviewsWorkspace() {
  const reviews = await api(`/api/projects/${state.projectId}/reviews`);
  const ws = document.getElementById("stage-workspace");
  ws.innerHTML = `<h2>Reviews</h2>${reviews.length ? reviews.map((r) => `<div class="history-item verdict-${r.verdict}"><strong>${r.stage}</strong>: ${r.verdict} - ${r.created_at || ""}${r.comment ? `<div>${escapeHtml(r.comment)}</div>` : ""}</div>`).join("") : "<p style='color:var(--text-dim)'>No reviews recorded.</p>"}`;
}

async function renderAssetsWorkspace() {
  const [assets, capabilities] = await Promise.all([
    api(`/api/projects/${state.projectId}/assets`),
    api("/api/capabilities"),
  ]);
  const ws = document.getElementById("stage-workspace");
  ws.innerHTML = `
    <h2>Assets</h2>
    <div class="section-title">Imported Assets</div>
    ${assets.length ? assets.map((a) => `<div class="history-item">${a.capability} - ${escapeHtml(a.file_path)} - ${a.created_at || ""}</div>`).join("") : "<p style='color:var(--text-dim);font-size:12px;'>No assets imported yet.</p>"}
    <div class="section-title">Import Asset (UI-provider capability)</div>
    <select id="import-capability">
      ${capabilities.filter((c) => c.execution_mode === "ui").map((c) => `<option value="${c.capability}">${c.capability} (${c.provider_id}${c.available ? "" : " - not integrated"})</option>`).join("")}
    </select>
    <input type="file" id="import-file" style="margin-top:8px;">
    <div class="stage-actions"><button id="import-btn" class="btn btn-primary">Import</button></div>`;

  document.getElementById("import-btn").onclick = async () => {
    const capability = document.getElementById("import-capability").value;
    const fileInput = document.getElementById("import-file");
    if (!fileInput.files.length) { toast("Choose a file first", true); return; }
    const fd = new FormData();
    fd.append("file", fileInput.files[0]);
    try {
      await api(`/api/projects/${state.projectId}/import?capability=${encodeURIComponent(capability)}`, { method: "POST", body: fd });
      toast("Asset imported");
      renderAssetsWorkspace();
    } catch (e) {
      toast(e.message, true);
    }
  };
}

async function renderSettingsWorkspace() {
  const capabilities = await api("/api/capabilities");
  const ws = document.getElementById("stage-workspace");
  ws.innerHTML = `
    <h2>Settings</h2>
    <div class="section-title">Providers (Capability Registry - display only)</div>
    ${capabilities.map((c) => `<div class="info-row"><span>${c.capability} &rarr; ${c.provider_id} (${c.execution_mode})</span><span class="v">${c.available ? "available" : "not integrated"}</span></div>`).join("")}
    <p style="font-size:11px;color:var(--text-dim);margin-top:14px;line-height:1.5;">
      Only capabilities registered in engine/packs/capability_registry.py appear here.
      Additional providers (Gemma, Llama, Kokoro, XTTS, Google Flow Music, OpenArt,
      Higgsfield, Runway) are not yet registered - see the Sprint 2A report.
      Target Platforms, Aspect Ratios, Quality Target, and Execution Mode are not
      configurable here because the engine has no such settings yet.
    </p>`;
}

// ---------- Command palette ----------

const COMMANDS = [
  { label: "Create Project", run: () => document.getElementById("new-project-btn").click() },
  { label: "Generate Story", run: () => requireProject() && selectStage("story") },
  { label: "Generate Screenplay", run: () => requireProject() && selectStage("screenplay") },
  { label: "Generate Audio", run: () => requireProject() && selectStage("audio") },
  { label: "Generate Motion Poster Prompt", run: () => requireProject() && selectStage("prompt") },
  { label: "Export Project", run: () => requireProject() && selectStage("export") },
  { label: "Review Stage", run: () => requireProject() && selectStage("reviews") },
  { label: "Import Asset", run: () => requireProject() && selectStage("assets") },
];

function requireProject() {
  if (!state.projectId) { toast("Open a project first", true); return false; }
  return true;
}

function renderPalette(filter = "") {
  const list = document.getElementById("palette-list");
  list.innerHTML = "";
  COMMANDS.filter((c) => c.label.toLowerCase().includes(filter.toLowerCase())).forEach((c) => {
    const li = document.createElement("li");
    li.textContent = c.label;
    li.onclick = () => { closePalette(); c.run(); };
    list.appendChild(li);
  });
}

function openPalette() {
  document.getElementById("command-palette").classList.remove("hidden");
  const input = document.getElementById("palette-input");
  input.value = "";
  renderPalette();
  input.focus();
}
function closePalette() {
  document.getElementById("command-palette").classList.add("hidden");
}

document.getElementById("palette-input").oninput = (e) => renderPalette(e.target.value);
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "k") {
    e.preventDefault();
    openPalette();
  } else if (e.key === "Escape") {
    closePalette();
    document.getElementById("new-project-dialog").classList.add("hidden");
  }
});
document.getElementById("command-palette").onclick = (e) => {
  if (e.target.id === "command-palette") closePalette();
};

// ---------- Boot ----------

renderHome();
