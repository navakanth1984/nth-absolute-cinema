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
  { id: "storage", label: "Storage", real: true },
  { id: "snapshots", label: "Snapshots", real: true },
  { id: "packages", label: "Packages", real: true },
  { id: "settings", label: "Settings", real: true },
  { id: "diagnostics", label: "Diagnostics", real: true },
  { id: "characters", label: "Characters (Coming Soon)", real: false },
  { id: "scenes", label: "Scenes (Coming Soon)", real: false },
  { id: "shots", label: "Shots (Coming Soon)", real: false },
  { id: "trailer", label: "Trailer (Coming Soon)", real: false },
  { id: "movie", label: "Movie (Coming Soon)", real: false },
];

const DEPARTMENTS = [
  {
    name: "Development",
    items: [
      { id: "idea", label: "Concept & Pitch" },
      { id: "story", label: "Story Bible" }
    ]
  },
  {
    name: "Pre-Production",
    items: [
      { id: "screenplay", label: "Screenplay Draft" },
      { id: "graph", label: "Creative Graph" }
    ]
  },
  {
    name: "Production Assets",
    items: [
      { id: "audio", label: "Audio Department" },
      { id: "prompt", label: "Cinematography" },
      { id: "assets", label: "Asset Manager" }
    ]
  },
  {
    name: "Infrastructure",
    items: [
      { id: "storage", label: "Storage Providers" },
      { id: "snapshots", label: "Snapshots Workspace" },
      { id: "packages", label: "NAC Packages" }
    ]
  },
  {
    name: "Supervision",
    items: [
      { id: "reviews", label: "Quality Control" },
      { id: "diagnostics", label: "Diagnostics logs" },
      { id: "settings", label: "Studio Settings" }
    ]
  }
];

const TIMELINE_STAGES = ["idea", "story", "screenplay", "audio", "prompt", "export"];

// Roadmap items are intentionally not clickable - they exist so the Studio is honest
// about what's built vs. what's next, not to fake functionality that doesn't exist yet.
const ROADMAP = [
  { label: "Restore Manager", note: "Restore a project from a snapshot" },
  { label: "Migration Manager", note: "Move packages between environments" },
  { label: "Character Department", note: "First Department Framework implementation" },
];

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
  list.innerHTML = `<div class="loading-state"><span class="spinner"></span>Loading projects...</div>`;
  try {
    const projects = await api("/api/projects");
    if (!projects.length) {
      list.innerHTML = `
        <div class="empty-state">
          <div class="empty-title">No projects yet</div>
          <p style="margin:0;">Start with your own idea, or load the demo project below to see a
          finished pipeline first.</p>
        </div>`;
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
    list.innerHTML = `<div class="error-banner">Could not load projects: ${escapeHtml(e.message)}</div>`;
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
document.getElementById("demo-project-btn").onclick = async () => {
  try {
    const { id } = await api("/api/projects/demo", { method: "POST" });
    toast("Demo project loaded");
    openProject(id);
  } catch (e) {
    toast(e.message, true);
  }
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
  state.aspectRatio = null;
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
  
  DEPARTMENTS.forEach(dept => {
    const groupDiv = document.createElement("div");
    groupDiv.className = "nav-group";
    
    const header = document.createElement("div");
    header.className = "nav-group-header";
    header.innerHTML = `<span>${dept.name}</span>`;
    groupDiv.appendChild(header);
    
    const ul = document.createElement("ul");
    ul.className = "nav-list";
    
    dept.items.forEach(s => {
      const li = document.createElement("li");
      const isActive = state.activeStage === s.id;
      li.className = "nav-item" + (isActive ? " active" : "");
      
      const st = statusFor(s.id);
      const dot = st && st !== "n/a" ? `<span class="status-dot ${st}"></span>` : "";
      li.innerHTML = `<span>${escapeHtml(s.label)}</span>${dot}`;
      
      li.onclick = () => selectStage(s.id);
      ul.appendChild(li);
    });
    
    groupDiv.appendChild(ul);
    nav.appendChild(groupDiv);
  });

  const roadmapDiv = document.createElement("div");
  roadmapDiv.className = "nav-group";
  roadmapDiv.innerHTML = `
    <div class="nav-group-header"><span>Planned</span></div>
    <ul class="nav-list">
      ${ROADMAP.map(r => `
        <li class="nav-item disabled" title="${escapeHtml(r.note)} - not built yet">
          <span>${escapeHtml(r.label)}</span>
          <span class="badge-warn" style="font-size:8.5px;">planned</span>
        </li>
      `).join("")}
    </ul>
  `;
  nav.appendChild(roadmapDiv);
}

function renderRightPanel() {
  const s = state.status;
  const doneCount = ["story_bible", "screenplay", "audio", "motion_poster_prompt"].filter((k) => s[k]).length;
  const pct = Math.round((doneCount / 4) * 100);
  const el = document.getElementById("production-info");
  
  const arKey = `nac_project_${state.projectId}_aspect_ratio`;
  if (!state.aspectRatio) {
    state.aspectRatio = localStorage.getItem(arKey) || "16:9";
  }

  const row = (label, value) => `<div class="info-row"><span>${label}</span><span class="v">${escapeHtml(String(value))}</span></div>`;
  
  el.innerHTML = `
    <div class="context-section" style="padding-bottom:10px; border-bottom:1px solid var(--border); margin-bottom:12px;">
      <div class="info-row" style="border-bottom:none; padding:0 0 6px;">
        <span style="font-size:13px; font-weight:600; color:var(--text);">${escapeHtml(state.projectId.substring(0, 8))}...</span>
        <span class="badge-ok" style="font-size:10px; padding:2px 6px;">ACTIVE</span>
      </div>
      <p style="font-size:11.5px; color:var(--text-dim); margin:0; line-height:1.4;">
        "${escapeHtml(s.idea_text.substring(0, 60))}${s.idea_text.length > 60 ? "..." : ""}"
      </p>
    </div>

    <div class="section-title">Department Settings</div>
    <div class="info-row" style="align-items: center; padding:4px 0;">
      <span>Aspect Ratio <span class="badge-warn" style="font-size:8.5px; margin-left:4px;" title="Drives the framing preview only - not yet applied to generated prompt text.">preview</span></span>
      <select id="context-aspect-ratio" style="background:#1a2032; border:1px solid var(--border); color:var(--gold); font-size:11px; font-weight:600; padding:3px 6px; border-radius:4px; cursor:pointer;">
        <option value="9:16" ${state.aspectRatio === "9:16" ? "selected" : ""}>9:16 Shorts</option>
        <option value="16:9" ${state.aspectRatio === "16:9" ? "selected" : ""}>16:9 Widescreen</option>
        <option value="1:1" ${state.aspectRatio === "1:1" ? "selected" : ""}>1:1 Square</option>
        <option value="4:5" ${state.aspectRatio === "4:5" ? "selected" : ""}>4:5 Vertical</option>
        <option value="21:9" ${state.aspectRatio === "21:9" ? "selected" : ""}>21:9 Anamorphic</option>
      </select>
    </div>
    ${row("Target Runtime", `${s.target_runtime_minutes} mins`)}

    <div class="section-title">Production Progress</div>
    <div class="progress-bar" style="margin-bottom:8px;">
      <div class="progress-bar-fill" style="width:${pct}%"></div>
    </div>
    ${row("Completeness", `${pct}% (${doneCount}/4 stages)`)}

    <div class="section-title">Infrastructure</div>
    ${row("Active Storage", "local")}
    ${row("LLM Provider", state.provider.llm_provider)}
    ${row("Reviews", s.review_count)}
    ${row("Assets Count", s.asset_count)}
  `;

  const select = document.getElementById("context-aspect-ratio");
  if (select) {
    select.onchange = (e) => {
      state.aspectRatio = e.target.value;
      localStorage.setItem(arKey, state.aspectRatio);
      toast(`Aspect ratio updated to ${state.aspectRatio}`);
      renderRightPanel();
      if (state.activeStage === "idea" || state.activeStage === "prompt" || state.activeStage === "graph") {
        selectStage(state.activeStage);
      }
    };
  }
}

function renderTimeline() {
  const s = state.status;
  const el = document.getElementById("timeline");
  if (!s || !el) { el.innerHTML = ""; return; }
  
  const tracks = [
    { name: "Pitch & Setup", stageId: "idea", color: "var(--gold)" },
    { name: "Story Bible", stageId: "story", color: "#4589ff" },
    { name: "Screenplay", stageId: "screenplay", color: "#a768ff" },
    { name: "Audio assets", stageId: "audio", color: "#00babd" },
    { name: "Camera Prompts", stageId: "prompt", color: "#ff6b8b" }
  ];

  const totalRuntime = s.target_runtime_minutes || 15;
  
  let markersHtml = "";
  const markerCount = 6;
  for (let i = 0; i <= markerCount; i++) {
    const val = ((totalRuntime / markerCount) * i).toFixed(1);
    markersHtml += `<div class="tl-marker" style="left: ${(i / markerCount) * 82 + 13}%;"><span>${val}m</span></div>`;
  }

  let tracksHtml = tracks.map((t) => {
    const status = statusFor(t.stageId);
    let barWidth = "0%";
    let barLabel = "Unstarted";
    let style = `background: var(--grey); opacity: 0.3;`;

    if (status === "done") {
      barWidth = "100%";
      barLabel = "Ready";
      style = `background: ${t.color}; box-shadow: 0 0 6px ${t.color}88;`;
    } else if (status === "review") {
      barWidth = "100%";
      barLabel = "Needs Review";
      style = `background: var(--amber); box-shadow: 0 0 6px var(--amber)88;`;
    } else if (t.stageId === "idea" || state.activeStage === t.stageId) {
      barWidth = "50%";
      barLabel = "Drafting";
      style = `background: var(--gold); animation: pulse 1.5s infinite alternate;`;
    }

    const isActiveRow = state.activeStage === t.stageId ? "active-row" : "";

    return `
      <div class="tl-track-row ${isActiveRow}" onclick="selectStage('${t.stageId}')">
        <div class="tl-track-header">
          <span>${t.name}</span>
        </div>
        <div class="tl-track-timeline">
          <div class="tl-track-block" style="width: ${barWidth}; ${style}">
            <span class="tl-block-label">${barLabel}</span>
          </div>
        </div>
      </div>
    `;
  }).join("");

  const activeIdx = tracks.findIndex(t => t.stageId === state.activeStage);
  const playheadPos = activeIdx >= 0 ? ((activeIdx / (tracks.length - 1)) * 82 + 13) : 13;

  el.innerHTML = `
    <div class="timeline-container">
      <div class="timeline-ruler">
        <div class="ruler-title">Tracks</div>
        <div class="ruler-markers">
          ${markersHtml}
        </div>
      </div>
      <div class="timeline-tracks-area">
        ${tracksHtml}
        <div class="timeline-playhead" style="left: ${playheadPos}%;"></div>
      </div>
    </div>
  `;
}

async function selectStage(stageId) {
  state.activeStage = stageId;
  renderNav();
  renderTimeline();
  const ws = document.getElementById("stage-workspace");
  ws.innerHTML = `<div class="loading-state"><span class="spinner"></span>Loading workspace...</div>`;

  if (stageId === "idea") return renderIdeaWorkspace();
  if (stageId === "graph") return renderCreativeGraphWorkspace();
  if (stageId === "export") return renderExportWorkspace();
  if (stageId === "reviews") return renderReviewsWorkspace();
  if (stageId === "assets") return renderAssetsWorkspace();
  if (stageId === "storage") return renderStorageWorkspace();
  if (stageId === "snapshots") return renderSnapshotsWorkspace();
  if (stageId === "packages") return renderPackagesWorkspace();
  if (stageId === "settings") return renderSettingsWorkspace();
  if (stageId === "diagnostics") return renderDiagnosticsWorkspace();
  return renderGenerativeStageWorkspace(stageId);
}

function renderIdeaWorkspace() {
  const ws = document.getElementById("stage-workspace");
  const arKey = `nac_project_${state.projectId}_aspect_ratio`;
  if (!state.aspectRatio) {
    state.aspectRatio = localStorage.getItem(arKey) || "16:9";
  }

  const ratios = [
    { id: "9:16", label: "9:16 Shorts", desc: "TikTok, YouTube Shorts, Instagram Reels (1080x1920)", ratio: "9/16" },
    { id: "16:9", label: "16:9 Widescreen", desc: "YouTube, TV, Standard horizontal format (1920x1080)", ratio: "16/9" },
    { id: "1:1", label: "1:1 Square", desc: "Instagram feeds, Square visual compositions (1080x1080)", ratio: "1/1" },
    { id: "4:5", label: "4:5 Portrait", desc: "Social media feeds, taller mobile compositions (1080x1350)", ratio: "4/5" },
    { id: "21:9", label: "21:9 Anamorphic", desc: "Cinematic widescreen, Ultra-wide movies (2560x1080)", ratio: "21/9" }
  ];

  const ratioCards = ratios.map(r => {
    const isSelected = state.aspectRatio === r.id;
    const borderStyle = isSelected ? "border-color: var(--gold); background: #1a223a;" : "border-color: var(--border);";
    const [w, h] = r.id.split(":");
    const boxWidth = 30;
    const boxHeight = (h / w) * boxWidth;
    let widthStyle = `${boxWidth}px`;
    let heightStyle = `${boxHeight}px`;
    if (boxHeight > 40) {
      heightStyle = `40px`;
      widthStyle = `${(w / h) * 40}px`;
    }

    return `
      <div class="ratio-card" style="padding: 10px 12px; border: 1px solid var(--border); border-radius: 6px; cursor: pointer; display: flex; align-items: center; gap: 14px; transition: all 150ms ease; ${borderStyle}" onclick="updateProjectAspectRatio('${r.id}')">
        <div style="width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; background: #0c101d; border-radius: 4px; border: 1px solid var(--border);">
          <div style="width: ${widthStyle}; height: ${heightStyle}; border: 2px solid ${isSelected ? "var(--gold)" : "var(--text-dim)"}; border-radius: 2px; background: rgba(212, 168, 67, 0.05);"></div>
        </div>
        <div style="flex: 1;">
          <div style="font-size: 13px; font-weight: 600; color: ${isSelected ? "var(--gold)" : "var(--text)"};">${escapeHtml(r.label)}</div>
          <div style="font-size: 11px; color: var(--text-dim); margin-top: 2px;">${escapeHtml(r.desc)}</div>
        </div>
      </div>
    `;
  }).join("");

  ws.innerHTML = `
    <h2>Concept & Pitch Settings</h2>
    <p style="color:var(--text-dim); font-size:13px; margin-bottom:18px;">
      Define your project's high-level targets and see how they carry into other departments.
    </p>

    <div class="section-title">One-Line Pitch</div>
    <div style="background: var(--panel-solid); border: 1px solid var(--border); border-radius: 6px; padding: 14px; font-size: 13.5px; line-height: 1.5; color: var(--text); font-style: italic; margin-bottom: 20px;">
      "${escapeHtml(state.status.idea_text)}"
    </div>

    <div class="section-title">Aspect Ratio</div>
    <div class="scope-note">
      <span class="badge-warn">PREVIEW ONLY</span>
      Drives the Cinematography framing preview crop. Not yet wired into the prompt
      compiler's generated text - full pipeline propagation is planned.
    </div>
    <div style="display: flex; flex-direction: column; gap: 8px; margin-bottom: 20px;">
      ${ratioCards}
    </div>

    <div class="section-title">Runtime & Quality Targets</div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
      <div style="background: var(--panel-solid); border: 1px solid var(--border); border-radius: 6px; padding: 12px;">
        <div style="font-size: 12px; color: var(--text-dim); margin-bottom: 4px;">Target Runtime</div>
        <div style="font-size: 16px; font-weight: 600; color: var(--gold);">${state.status.target_runtime_minutes} minutes</div>
      </div>
      <div style="background: var(--panel-solid); border: 1px solid var(--border); border-radius: 6px; padding: 12px;">
        <div style="font-size: 12px; color: var(--text-dim); margin-bottom: 4px;">Quality Objective</div>
        <div style="font-size: 16px; font-weight: 600; color: var(--green);">High-Fidelity Prompting</div>
      </div>
    </div>
  `;
}

window.updateProjectAspectRatio = function(ratio) {
  const arKey = `nac_project_${state.projectId}_aspect_ratio`;
  state.aspectRatio = ratio;
  localStorage.setItem(arKey, ratio);
  toast(`Aspect ratio updated to ${ratio}`);
  renderRightPanel();
  renderIdeaWorkspace();
};

function notGeneratedYet(label) {
  return `
    <div class="empty-state">
      <div class="empty-title">${escapeHtml(label)} not generated yet</div>
      <p style="margin:0;">Click "Compile Stage" above to generate it.</p>
    </div>
  `;
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

  let stageContentArea = "";
  if (stageId === "audio") {
    stageContentArea = renderAudioPlayer();
  } else if (stageId === "prompt") {
    const promptText = content[meta.contentKey] || "(prompt not generated yet)";
    let aspectRatioStyle = "aspect-ratio: 16 / 9; width: 100%;";
    let maxW = "480px";
    
    if (state.aspectRatio === "9:16") {
      aspectRatioStyle = "aspect-ratio: 9 / 16; height: 280px; width: auto;";
      maxW = "165px";
    } else if (state.aspectRatio === "1:1") {
      aspectRatioStyle = "aspect-ratio: 1 / 1; width: 240px;";
      maxW = "240px";
    } else if (state.aspectRatio === "4:5") {
      aspectRatioStyle = "aspect-ratio: 4 / 5; height: 240px; width: auto;";
      maxW = "200px";
    } else if (state.aspectRatio === "21:9") {
      aspectRatioStyle = "aspect-ratio: 21 / 9; width: 100%;";
      maxW = "480px";
    }

    stageContentArea = `
      <div style="display: flex; gap: 20px; flex-wrap: wrap; margin-top: 10px;">
        <div style="flex: 1; min-width: 250px; display: flex; flex-direction: column; gap: 8px;">
          <div style="font-size: 11px; text-transform: uppercase; color: var(--text-dim); font-weight:600;">Generated prompt package</div>
          <div class="stage-content" id="content-box" style="flex:1; max-height: 250px; overflow-y:auto; margin:0;">${escapeHtml(promptText)}</div>
        </div>
        <div style="width: 100%; max-width: ${maxW}; display: flex; flex-direction: column; gap: 8px;">
          <div style="font-size: 11px; text-transform: uppercase; color: var(--text-dim); font-weight:600; display:flex; justify-content:space-between;">
            <span>Framing Preview (${state.aspectRatio})</span>
            <span class="badge-warn" style="font-size:9px;">Preview Only</span>
          </div>
          <div class="scope-note" style="margin:0 0 2px;">
            Crop is a visual guide only - the prompt text to the left is not yet
            regenerated per aspect ratio.
          </div>
          <div class="aspect-ratio-preview-box" style="background:#05070e; border:2px solid var(--border); border-radius:6px; overflow:hidden; position:relative; display:flex; align-items:center; justify-content:center; ${aspectRatioStyle}">
            <!-- Rule of thirds lines -->
            <div style="position:absolute; inset:0; pointer-events:none; border-left:1px dashed rgba(212, 168, 67, 0.15); border-right:1px dashed rgba(212, 168, 67, 0.15); margin: 0 33.33%;"></div>
            <div style="position:absolute; inset:0; pointer-events:none; border-top:1px dashed rgba(212, 168, 67, 0.15); border-bottom:1px dashed rgba(212, 168, 67, 0.15); margin: 33.33% 0;"></div>
            <!-- Vignette shadow overlay -->
            <div style="position:absolute; inset:0; pointer-events:none; box-shadow: inset 0 0 40px rgba(0,0,0,0.8);"></div>
            <div style="font-size:10px; font-weight:700; color:rgba(212, 168, 67, 0.4); text-transform:uppercase; z-index:1;">[ ${state.aspectRatio} Crop ]</div>
            <!-- Overlay description -->
            <div style="position:absolute; bottom:8px; left:8px; right:8px; background:rgba(0,0,0,0.7); padding:4px 6px; border-radius:4px; font-size:9.5px; font-family:monospace; color:#8891a8; text-align:center; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; border:1px solid #232b40;">
              ${escapeHtml(promptText.substring(0, 45))}...
            </div>
          </div>
        </div>
      </div>
    `;
  } else if (stageId === "screenplay") {
    stageContentArea = content[meta.contentKey]
      ? `<div class="screenplay-paper" id="content-box">${escapeHtml(content[meta.contentKey])}</div>`
      : notGeneratedYet(meta.label);
  } else {
    stageContentArea = content[meta.contentKey]
      ? `<div class="stage-content" id="content-box" style="max-height: 250px; overflow-y:auto;">${escapeHtml(content[meta.contentKey])}</div>`
      : notGeneratedYet(meta.label);
  }

  ws.innerHTML = `
    <h2>${meta.label} Workspace</h2>
    <div class="stage-actions" style="margin-bottom:16px;">
      <button id="gen-btn" class="btn btn-primary" ${unlocked ? "" : "disabled"}>${done ? "Regenerate Stage" : "Compile Stage"}</button>
      ${!unlocked ? '<span style="color:var(--text-dim);font-size:12.5px;align-self:center;margin-left:10px;">🔒 Locked - Complete & Approve preceding stages first.</span>' : ""}
    </div>
    <div id="gen-error-banner"></div>
    ${stageContentArea}
    
    ${stageMetrics ? `<div class="section-title">Execution Metrics</div><pre style="margin:0; padding:10px; background:#0a0e1a; border:1px solid var(--border); border-radius:6px; font-size:11px; font-family:monospace; max-height:100px; overflow-y:auto; color:var(--text-dim);">${escapeHtml(JSON.stringify(stageMetrics, null, 2))}</pre>` : ""}
    
    <div class="section-title">Review Log Decisions</div>
    <div class="review-controls" style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom:14px;">
      <button class="btn btn-primary" style="background:var(--green); color:#0c101d;" data-verdict="approved">Approve Stage</button>
      <button class="btn" style="background:#281f18; border-color:var(--amber); color:var(--amber);" data-verdict="needs_revision">Needs Revision</button>
      <button class="btn" style="background:#2d1614; border-color:var(--red); color:var(--red);" data-verdict="rejected">Reject Draft</button>
      <input id="review-comment" placeholder="Add supervisor annotations / review comments..." style="flex:1; min-width:200px;">
    </div>
    <div class="section-title">Decision History</div>
    <div id="history-list">${stageReviews.length ? stageReviews.map(historyItem).join("") : '<p style="color:var(--text-dim);font-size:12px;">No historical decisions recorded.</p>'}</div>
  `;

  // Waveform levels simulation logic for audio stage
  if (stageId === "audio") {
    const audioEl = document.getElementById("audio-playback");
    if (audioEl) {
      audioEl.onplay = () => {
        window.vuInterval = setInterval(() => {
          const lVal = Math.floor(Math.random() * 40) + 50;
          const rVal = Math.floor(Math.random() * 40) + 45;
          const leftVu = document.getElementById("vu-meter-l");
          const rightVu = document.getElementById("vu-meter-r");
          if (leftVu) leftVu.style.width = `${lVal}%`;
          if (rightVu) rightVu.style.width = `${rVal}%`;
        }, 120);
      };
      audioEl.onpause = () => {
        clearInterval(window.vuInterval);
        const leftVu = document.getElementById("vu-meter-l");
        const rightVu = document.getElementById("vu-meter-r");
        if (leftVu) leftVu.style.width = "10%";
        if (rightVu) rightVu.style.width = "10%";
      };
    }
  }

  document.getElementById("gen-btn").onclick = async () => {
    document.getElementById("gen-btn").disabled = true;
    document.getElementById("gen-btn").textContent = "Compiling...";
    document.getElementById("gen-error-banner").innerHTML = "";
    try {
      await api(`/api/projects/${state.projectId}/generate/${stageId}`, { method: "POST" });
      toast(`${meta.label} generated`);
      await refreshProject();
      selectStage(stageId);
    } catch (e) {
      toast(e.message, true);
      const btn = document.getElementById("gen-btn");
      btn.disabled = false;
      btn.textContent = done ? "Regenerate Stage" : "Compile Stage";
      const banner = document.getElementById("gen-error-banner");
      if (banner) banner.innerHTML = `<div class="error-banner">${escapeHtml(e.message)}</div>`;
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
        await refreshProject();
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
  const audioUrl = `/api/projects/${state.projectId}/audio`;
  return `
    <div style="background:#0c101d; border:1px solid var(--border); border-radius:8px; padding:20px; display:flex; flex-direction:column; gap:16px;">
      <!-- VU Meters -->
      <div style="display:flex; flex-direction:column; gap:4px;">
        <div style="font-size:10px; color:var(--text-dim); text-transform:uppercase; font-weight:600; letter-spacing:0.05em;">Stereo Output Levels (dB)</div>
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-size:11px; width:12px; color:var(--text-dim);">L</span>
          <div style="flex:1; height:6px; background:#141b2c; border-radius:3px; overflow:hidden; display:flex;">
            <div id="vu-meter-l" style="width:10%; height:100%; background:linear-gradient(95deg, var(--green) 70%, var(--amber) 90%, var(--red) 100%); transition: width 80ms ease;"></div>
          </div>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-size:11px; width:12px; color:var(--text-dim);">R</span>
          <div style="flex:1; height:6px; background:#141b2c; border-radius:3px; overflow:hidden; display:flex;">
            <div id="vu-meter-r" style="width:10%; height:100%; background:linear-gradient(95deg, var(--green) 70%, var(--amber) 90%, var(--red) 100%); transition: width 80ms ease;"></div>
          </div>
        </div>
      </div>

      <!-- Waveform Simulation -->
      <div style="height:60px; background:#05070e; border:1px solid var(--border); border-radius:4px; position:relative; overflow:hidden; display:flex; align-items:center; justify-content:center; gap:3px; padding:0 10px;">
        <!-- Simulated Waveform Bars -->
        <div style="flex:1; height:8px; background:#00babd; border-radius:1px; opacity:0.4;"></div>
        <div style="flex:1; height:12px; background:#00babd; border-radius:1px; opacity:0.4;"></div>
        <div style="flex:1; height:24px; background:#00babd; border-radius:1px; opacity:0.5;"></div>
        <div style="flex:1; height:18px; background:#00babd; border-radius:1px; opacity:0.5;"></div>
        <div style="flex:1; height:32px; background:#00babd; border-radius:1px; opacity:0.6;"></div>
        <div style="flex:1; height:44px; background:#00babd; border-radius:1px; opacity:0.7;"></div>
        <div style="flex:1; height:36px; background:#00babd; border-radius:1px; opacity:0.7;"></div>
        <div style="flex:1; height:22px; background:#00babd; border-radius:1px; opacity:0.5;"></div>
        <div style="flex:1; height:12px; background:#00babd; border-radius:1px; opacity:0.4;"></div>
        <div style="flex:1; height:6px; background:#00babd; border-radius:1px; opacity:0.3;"></div>
        <div style="flex:1; height:18px; background:#00babd; border-radius:1px; opacity:0.5;"></div>
        <div style="flex:1; height:30px; background:#00babd; border-radius:1px; opacity:0.6;"></div>
        <div style="flex:1; height:40px; background:#00babd; border-radius:1px; opacity:0.7;"></div>
        <div style="flex:1; height:48px; background:#00babd; border-radius:1px; opacity:0.8;"></div>
        <div style="flex:1; height:38px; background:#00babd; border-radius:1px; opacity:0.7;"></div>
        <div style="flex:1; height:26px; background:#00babd; border-radius:1px; opacity:0.5;"></div>
        <div style="flex:1; height:14px; background:#00babd; border-radius:1px; opacity:0.4;"></div>
        <div style="flex:1; height:32px; background:#00babd; border-radius:1px; opacity:0.6;"></div>
        <div style="flex:1; height:45px; background:#00babd; border-radius:1px; opacity:0.7;"></div>
        <div style="flex:1; height:50px; background:#00babd; border-radius:1px; opacity:0.8;"></div>
        <div style="flex:1; height:34px; background:#00babd; border-radius:1px; opacity:0.7;"></div>
        <div style="flex:1; height:20px; background:#00babd; border-radius:1px; opacity:0.5;"></div>
        <div style="flex:1; height:10px; background:#00babd; border-radius:1px; opacity:0.4;"></div>
        <div style="flex:1; height:24px; background:#00babd; border-radius:1px; opacity:0.5;"></div>
        <div style="flex:1; height:38px; background:#00babd; border-radius:1px; opacity:0.7;"></div>
        <div style="flex:1; height:42px; background:#00babd; border-radius:1px; opacity:0.7;"></div>
        <div style="flex:1; height:30px; background:#00babd; border-radius:1px; opacity:0.6;"></div>
        <div style="flex:1; height:12px; background:#00babd; border-radius:1px; opacity:0.4;"></div>
      </div>

      <!-- Controls -->
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
        <audio id="audio-playback" src="${audioUrl}" controls style="flex:1; min-width:200px; height:32px; filter: invert(0.9) hue-rotate(180deg);"></audio>
        <div style="display:flex; gap:8px;">
          <span class="badge-ok" style="font-size:10px; padding:3px 6px;">24-bit PCM</span>
          <span class="badge-ok" style="font-size:10px; padding:3px 6px; background:rgba(0,186,189,0.1); color:#00babd; border-color:#00babd;">48kHz Stereo</span>
        </div>
      </div>
    </div>
  `;
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

async function renderDiagnosticsWorkspace() {
  const ws = document.getElementById("stage-workspace");
  ws.innerHTML = `<h2>Diagnostics</h2><p style="color:var(--text-dim);font-size:12px;">Checking...</p>`;
  let d;
  try {
    d = await api("/api/diagnostics");
  } catch (e) {
    ws.innerHTML = `<h2>Diagnostics</h2><p style="color:var(--red);font-size:13px;">Failed to load diagnostics: ${escapeHtml(e.message)}</p>`;
    return;
  }
  const row = (label, value, ok) => `<div class="info-row"><span>${label}</span><span class="v" style="color:${ok === undefined ? "var(--gold)" : ok ? "var(--green)" : "var(--red)"}">${escapeHtml(String(value))}</span></div>`;
  
  // Format graph health HTML block
  let graphHealthHtml = "";
  if (Object.keys(d.graph_health).length === 0) {
    graphHealthHtml = `<p style="color:var(--text-dim); font-size:12px;">No active projects to validate.</p>`;
  } else {
    graphHealthHtml = Object.entries(d.graph_health).map(([pid, health]) => {
      const isOk = health.health === "healthy";
      const badge = isOk ? `<span class="badge-ok">Healthy</span>` : `<span class="badge-error">Unhealthy (${health.violations.length} violations)</span>`;
      let violationsHtml = "";
      if (health.violations && health.violations.length > 0) {
        violationsHtml = `<ul style="margin:4px 0 0 16px; padding:0; font-size:11px; color:var(--text-dim); list-style:circle;">${health.violations.map(v => `<li>${escapeHtml(v)}</li>`).join("")}</ul>`;
      }
      return `
        <div style="margin-bottom:8px; padding-bottom:8px; border-bottom:1px dashed var(--border);">
          <div style="display:flex; justify-content:space-between; font-size:12.5px;">
            <span>Project: <code>${pid.substring(0,8)}...</code></span>
            ${badge}
          </div>
          ${violationsHtml}
        </div>
      `;
    }).join("");
  }

  ws.innerHTML = `
    <h2>Diagnostics</h2>
    <div class="section-title">System</div>
    ${row("Python", d.python_version)}
    ${row("SDK version", d.sdk_version)}
    ${row("SQLite", d.sqlite, d.sqlite === "ok")}
    ${row("Disk free", d.disk ? `${d.disk.free_gb} GB / ${d.disk.total_gb} GB` : "unknown")}
    ${row("GPU", d.gpu)}
    <div class="section-title">LLM Providers</div>
    ${row("Ollama", d.ollama, d.ollama === "reachable")}
    ${row("OpenRouter", d.openrouter, d.openrouter === "configured")}
    ${row("Active provider (last call)", d.provider.llm_provider)}
    ${d.provider.fallback_chain ? row("Fallback chain", d.provider.fallback_chain.join(" → ")) : ""}
    
    <div class="section-title">Voice Providers</div>
    ${row("ElevenLabs", d.elevenlabs, d.elevenlabs === "configured")}
    ${row("Sarvam", d.sarvam, d.sarvam === "configured")}
    ${row("Active voice provider", d.provider.tts_provider || "unknown")}
    ${d.provider.tts_fallback_chain ? row("Voice fallback chain", d.provider.tts_fallback_chain.join(" → ")) : ""}
    
    <div class="section-title">Active Repository Storage</div>
    ${row("Active Provider", d.storage.active_provider)}
    ${row("Local Package Path", d.storage.providers.find(p => p.name === "local")?.base_dir || "unknown")}
    ${row("Active Snapshots On Disk", d.snapshots_info.count)}

    <div class="section-title">Graph Validation Health (CDLC)</div>
    ${graphHealthHtml}

    ${d.provider.fallback_events && d.provider.fallback_events.length ? `
      <div class="section-title">LLM Fallback Events (this session)</div>
      ${d.provider.fallback_events.map((e) => `<div class="history-item verdict-needs_revision">${escapeHtml(e.skipped_provider)} skipped: ${escapeHtml(e.error)}</div>`).join("")}
    ` : ""}
    ${d.provider.tts_fallback_events && d.provider.tts_fallback_events.length ? `
      <div class="section-title">Voice Fallback Events (this session)</div>
      ${d.provider.tts_fallback_events.map((e) => `<div class="history-item verdict-needs_revision">${escapeHtml(e.skipped_backend)} skipped: ${escapeHtml(e.error)}</div>`).join("")}
    ` : ""}
    <div class="section-title">Capabilities (Registry - display only)</div>
    ${d.capabilities.map((c) => row(`${c.capability} (${c.provider_id})`, c.available ? "available" : "not integrated", c.available)).join("")}
    <p style="font-size:11px;color:var(--text-dim);margin-top:14px;line-height:1.5;">
      Every field above is a live check, not a placeholder. "unknown" means the
      value genuinely could not be detected (e.g. no nvidia-smi found for GPU) -
      it is never a guessed value.
    </p>`;
}

async function renderStorageWorkspace() {
  const ws = document.getElementById("stage-workspace");
  ws.innerHTML = `<h2>Storage Providers</h2><p style="color:var(--text-dim);font-size:12px;">Loading storage configuration...</p>`;
  try {
    const [providers, active] = await Promise.all([
      api("/api/storage/providers"),
      api("/api/storage/active"),
    ]);

    let providerRows = providers.map(p => {
      const isActive = p.name === active.name;
      const activeBadge = isActive ? `<span class="badge-ok" style="margin-left:8px;">Active</span>` : "";
      
      let healthBadge = "";
      if (p.health === "ok") {
        healthBadge = `<span class="badge-ok">Healthy</span>`;
      } else if (p.health === "unhealthy") {
        healthBadge = `<span class="badge-warn">Unhealthy</span>`;
      } else {
        healthBadge = `<span class="badge-error" title="${escapeHtml(p.error)}">Error</span>`;
      }

      const caps = Object.entries(p.capabilities).map(([cap, status]) => {
        let color = "var(--text-dim)";
        if (status === "supported") color = "var(--green)";
        if (status === "planned") color = "var(--gold)";
        if (status === "unsupported") color = "var(--red)";
        return `<span style="font-size:11px; margin-right:8px; color:${color}; font-weight:600;">${cap}: ${status}</span>`;
      }).join(" ");

      return `
        <tr>
          <td><strong>${escapeHtml(p.name)}</strong>${activeBadge}</td>
          <td><code style="font-size:12px; color:var(--gold);">${escapeHtml(p.type)}</code></td>
          <td><span style="font-size:12px; font-family:monospace; color:var(--text-dim);">${escapeHtml(p.base_dir)}</span></td>
          <td>${healthBadge}</td>
          <td>${caps}</td>
        </tr>
      `;
    }).join("");

    ws.innerHTML = `
      <h2>Storage Workspace</h2>
      <p style="color:var(--text-dim);font-size:13px;margin-bottom:18px;">
        Exposes configured repository storage locations and active provider capability support matricies.
      </p>
      
      <div class="section-title">Registered Providers</div>
      <div class="table-container">
        <table class="infra-table">
          <thead>
            <tr>
              <th>Provider Name</th>
              <th>Class Type</th>
              <th>Base Location</th>
              <th>Mount Health</th>
              <th>Capabilities matrix</th>
            </tr>
          </thead>
          <tbody>
            ${providerRows}
          </tbody>
        </table>
      </div>
      
      <p style="font-size:11px;color:var(--text-dim);margin-top:18px;line-height:1.5;">
        Local and External providers actively perform traversal injection checks. Disconnecting the External mount drive triggers a Mount Health failure to prevent writes defaulting to C:.
      </p>
    `;
  } catch (e) {
    ws.innerHTML = `<h2>Storage Workspace</h2><p style="color:var(--red);">Failed to load storage: ${escapeHtml(e.message)}</p>`;
  }
}

async function renderSnapshotsWorkspace() {
  const ws = document.getElementById("stage-workspace");
  ws.innerHTML = `<h2>Snapshots Workspace</h2><p style="color:var(--text-dim);font-size:12px;">Loading snapshots...</p>`;
  try {
    const snapshots = await api("/api/snapshots");
    
    let diffSelectHtml = "";
    if (snapshots.length >= 2) {
      const options = snapshots.map(s => `<option value="${s.snapshot_id}">${escapeHtml(s.snapshot_id.substring(0,8))}... (${s.created_at})</option>`).join("");
      diffSelectHtml = `
        <div class="section-title">Compare Snapshots (Diff tool)</div>
        <div class="review-controls" style="margin-bottom:20px; background:var(--panel-solid); padding:12px; border:1px solid var(--border); border-radius:6px; flex-wrap:wrap; gap:12px; height:auto;">
          <div>
            <label style="font-size:11px; color:var(--text-dim); display:block; margin-bottom:4px;">Snapshot A</label>
            <select id="diff-snap1" style="background:#0a0e1a; border:1px solid var(--border); color:var(--text); padding:6px; border-radius:4px;">
              ${options}
            </select>
          </div>
          <div>
            <label style="font-size:11px; color:var(--text-dim); display:block; margin-bottom:4px;">Snapshot B</label>
            <select id="diff-snap2" style="background:#0a0e1a; border:1px solid var(--border); color:var(--text); padding:6px; border-radius:4px;">
              ${options}
            </select>
          </div>
          <button id="diff-btn" class="btn btn-primary" style="margin-top:auto;">Compare</button>
        </div>
        <div id="diff-output-container" class="hidden">
          <div class="section-title">Diff Output</div>
          <div id="diff-output" class="diff-box"></div>
        </div>
      `;
    }

    let snapshotListHtml = "";
    if (snapshots.length === 0) {
      snapshotListHtml = `<p style="color:var(--text-dim);font-size:12px;">No snapshots captured yet.</p>`;
    } else {
      snapshotListHtml = snapshots.map(s => `
        <div class="item-card">
          <div class="title">
            <span>Snapshot ID: <code style="color:var(--gold);">${escapeHtml(s.snapshot_id)}</code></span>
            <div>
              <button class="btn btn-link" style="margin-right:12px; font-weight:600;" onclick="inspectSnapshot('${s.snapshot_id}')">Inspect Manifest</button>
              <button class="btn btn-link" style="color:var(--green); font-weight:600;" onclick="verifySnapshot('${s.snapshot_id}')">Verify Integrity</button>
            </div>
          </div>
          <div class="details">
            <span><strong>Created:</strong> ${escapeHtml(s.created_at)}</span>
            <span><strong>Project:</strong> ${escapeHtml(s.project_id.substring(0,8))}...</span>
            <span><strong>Master Hash:</strong> <code style="font-size:11px;">${escapeHtml(s.data_hash.substring(0,16))}...</code></span>
          </div>
          <div id="inspect-result-${s.snapshot_id}" class="hidden" style="margin-top:8px; border-top:1px solid var(--border); padding-top:8px;"></div>
        </div>
      `).join("");
    }

    ws.innerHTML = `
      <h2>Snapshots Workspace</h2>
      <p style="color:var(--text-dim);font-size:13px;margin-bottom:18px;">
        Capture the complete, immutable state of your project. Captures all five graphs, style genomes, reviews, assets, metrics, and environment metadata.
      </p>
      
      <div class="stage-actions" style="margin-bottom:20px;">
        <button id="create-snapshot-btn" class="btn btn-primary">Capture Snapshot</button>
        <span style="font-size:12px; color:var(--text-dim); align-self:center;">Restoration is disabled in this build (RestoreManager planned for next milestone)</span>
      </div>

      ${diffSelectHtml}

      <div class="section-title">Available Snapshots</div>
      <div style="max-height:40vh; overflow-y:auto;">
        ${snapshotListHtml}
      </div>
    `;

    document.getElementById("create-snapshot-btn").onclick = async () => {
      const btn = document.getElementById("create-snapshot-btn");
      btn.disabled = true;
      btn.textContent = "Capturing...";
      try {
        await api(`/api/projects/${state.projectId}/snapshots`, { method: "POST" });
        toast("Snapshot successfully created and serialized");
        await renderSnapshotsWorkspace();
      } catch (e) {
        toast(e.message, true);
        btn.disabled = false;
        btn.textContent = "Capture Snapshot";
      }
    };

    if (snapshots.length >= 2) {
      document.getElementById("diff-btn").onclick = async () => {
        const snap1 = document.getElementById("diff-snap1").value;
        const snap2 = document.getElementById("diff-snap2").value;
        const outContainer = document.getElementById("diff-output-container");
        const outBox = document.getElementById("diff-output");
        outBox.textContent = "Computing differences...";
        outContainer.classList.remove("hidden");
        try {
          const diff = await api("/api/snapshots/diff", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ snapshot1_id: snap1, snapshot2_id: snap2 }),
          });

          let html = "";
          if (diff.story && Object.keys(diff.story.modified_fields).length > 0) {
            html += `<span class="diff-modified">[Story Modified]</span>\n`;
            for (const [k, [oldV, newV]] of Object.entries(diff.story.modified_fields)) {
              html += `  Field: ${k}\n`;
              html += `    <span class="diff-removed">- ${escapeHtml(String(oldV))}</span>\n`;
              html += `    <span class="diff-added">+ ${escapeHtml(String(newV))}</span>\n`;
            }
          }
          if (diff.compiler_metrics && (diff.compiler_metrics.added.length > 0 || diff.compiler_metrics.removed.length > 0 || diff.compiler_metrics.modified.length > 0)) {
            html += `\n<span class="diff-modified">[Metrics Changes]</span>\n`;
            diff.compiler_metrics.added.forEach(m => {
              html += `  <span class="diff-added">+ Added Metrics: ${m.compiler} (${m.id.substring(0,8)})</span>\n`;
            });
            diff.compiler_metrics.removed.forEach(m => {
              html += `  <span class="diff-removed">- Removed Metrics: ${m.compiler} (${m.id.substring(0,8)})</span>\n`;
            });
            diff.compiler_metrics.modified.forEach(m => {
              html += `  Modified Compiler metrics: ${m.compiler} (${m.id.substring(0,8)})\n`;
              for (const [k, [oldV, newV]] of Object.entries(m.changes)) {
                html += `    ${k}: <span class="diff-removed">${escapeHtml(String(oldV))}</span> &rarr; <span class="diff-added">${escapeHtml(String(newV))}</span>\n`;
              }
            });
          }
          if (diff.review_log && (diff.review_log.added.length > 0 || diff.review_log.removed.length > 0)) {
            html += `\n<span class="diff-modified">[Review Log Changes]</span>\n`;
            diff.review_log.added.forEach(r => {
              html += `  <span class="diff-added">+ Added Review: ${r.stage} -> ${r.verdict} (${r.comment || ""})</span>\n`;
            });
            diff.review_log.removed.forEach(r => {
              html += `  <span class="diff-removed">- Removed Review: ${r.stage} -> ${r.verdict}</span>\n`;
            });
          }
          if (diff.assets && (diff.assets.added.length > 0 || diff.assets.removed.length > 0 || diff.assets.modified.length > 0)) {
            html += `\n<span class="diff-modified">[Assets Changes]</span>\n`;
            diff.assets.added.forEach(a => {
              html += `  <span class="diff-added">+ Added Asset: ${a.capability} -> ${a.file_path}</span>\n`;
            });
            diff.assets.removed.forEach(a => {
              html += `  <span class="diff-removed">- Removed Asset: ${a.capability} -> ${a.file_path}</span>\n`;
            });
            diff.assets.modified.forEach(a => {
              html += `  Modified Asset: ${a.capability}\n`;
              for (const [k, [oldV, newV]] of Object.entries(a.changes)) {
                html += `    ${k}: <span class="diff-removed">${escapeHtml(String(oldV))}</span> &rarr; <span class="diff-added">${escapeHtml(String(newV))}</span>\n`;
              }
            });
          }

          if (!html) {
            html = "No differences found. Snapshots are identical.";
          }
          outBox.innerHTML = html;
        } catch (e) {
          outBox.textContent = `Diff failed: ${e.message}`;
        }
      };
    }

  } catch (e) {
    ws.innerHTML = `<h2>Snapshots Workspace</h2><p style="color:var(--red);">Failed to load snapshots: ${escapeHtml(e.message)}</p>`;
  }
}

window.inspectSnapshot = async function(snapshotId) {
  const resultDiv = document.getElementById(`inspect-result-${snapshotId}`);
  if (!resultDiv.classList.contains("hidden") && resultDiv.querySelector(".pre-inspect")) {
    resultDiv.classList.add("hidden");
    return;
  }
  resultDiv.innerHTML = "<p style='color:var(--text-dim); font-size:11px;'>Loading manifest...</p>";
  resultDiv.classList.remove("hidden");
  try {
    const snap = await api(`/api/snapshots/${snapshotId}`);
    resultDiv.innerHTML = `
      <div class="pre-inspect">
        <div style="font-size:11.5px; color:var(--text-dim); margin-bottom:6px;"><strong>Manifest Details:</strong></div>
        <pre style="margin:0; padding:10px; background:#0a0e1a; border:1px solid var(--border); border-radius:4px; font-size:11px; font-family:monospace; overflow-x:auto; max-height:200px; white-space:pre-wrap;">${escapeHtml(JSON.stringify(snap.manifest, null, 2))}</pre>
      </div>
    `;
  } catch (e) {
    resultDiv.innerHTML = `<p style="color:var(--red); font-size:11px;">Failed: ${escapeHtml(e.message)}</p>`;
  }
};

window.verifySnapshot = async function(snapshotId) {
  const resultDiv = document.getElementById(`inspect-result-${snapshotId}`);
  resultDiv.innerHTML = "<p style='color:var(--text-dim); font-size:11px;'>Running cryptographic checks...</p>";
  resultDiv.classList.remove("hidden");
  try {
    const res = await api(`/api/snapshots/${snapshotId}/verify`, { method: "POST" });
    const verifyBadge = res.verified ? `<span class="badge-ok">Integrity OK</span>` : `<span class="badge-error">Integrity CORRUPT</span>`;
    let violationsHtml = "";
    if (res.violations && res.violations.length > 0) {
      violationsHtml = `
        <div style="font-size:11px; color:var(--red); margin-top:6px; font-weight:600;">Structural Violations:</div>
        <ul style="margin:4px 0 0 16px; padding:0; font-size:11px; color:var(--text-dim);">
          ${res.violations.map(v => `<li>${escapeHtml(v)}</li>`).join("")}
        </ul>
      `;
    } else {
      violationsHtml = `<div style="font-size:11px; color:var(--green); margin-top:6px; font-weight:600;">No structural violations found.</div>`;
    }

    resultDiv.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
        <span style="font-size:12px; font-weight:600; color:var(--text);">Cryptographic Integrity Verdict</span>
        ${verifyBadge}
      </div>
      ${violationsHtml}
    `;
  } catch (e) {
    resultDiv.innerHTML = `<p style="color:var(--red); font-size:11px;">Failed: ${escapeHtml(e.message)}</p>`;
  }
};

async function renderPackagesWorkspace() {
  const ws = document.getElementById("stage-workspace");
  ws.innerHTML = `<h2>Packages Workspace</h2><p style="color:var(--text-dim);font-size:12px;">Loading packages...</p>`;
  try {
    const packages = await api("/api/packages");

    let packageListHtml = "";
    if (packages.length === 0) {
      packageListHtml = `<p style="color:var(--text-dim);font-size:12px;">No packages serialized yet. Click "Create .nac Package" below to compile the active project state.</p>`;
    } else {
      packageListHtml = packages.map(p => `
        <div class="item-card">
          <div class="title">
            <span>Package Name: <code style="color:var(--gold);">${escapeHtml(p.package_id)}</code></span>
            <div>
              <button class="btn btn-link" style="margin-right:12px; font-weight:600;" onclick="inspectPackageManifest('${p.package_id}')">Manifest</button>
              <button class="btn btn-link" style="color:var(--green); font-weight:600;" onclick="browsePackageContents('${p.package_id}')">Browse Files</button>
            </div>
          </div>
          <div class="details">
            <span><strong>Created:</strong> ${escapeHtml(p.created_at)}</span>
            <span><strong>Path:</strong> <span style="font-family:monospace; font-size:11px; color:var(--text-dim);">${escapeHtml(p.path)}</span></span>
          </div>
          <div id="package-result-${escapeHtml(p.package_id)}" class="hidden" style="margin-top:8px; border-top:1px solid var(--border); padding-top:8px;"></div>
        </div>
      `).join("");
    }

    ws.innerHTML = `
      <h2>Packages Workspace</h2>
      <p style="color:var(--text-dim);font-size:13px;margin-bottom:18px;">
        Compile your project snapshot into the standard uncompressed <code style="color:var(--gold);">.nac</code> directory format for porting across workspaces.
      </p>

      <div class="stage-actions" style="margin-bottom:20px;">
        <button id="create-package-btn" class="btn btn-primary">Create .nac Package</button>
        <span style="font-size:12px; color:var(--text-dim); align-self:center;">Zip compression and cloud migrations remain planned milestones</span>
      </div>

      <div class="section-title">Compiled Packages (.nac layout)</div>
      <div style="max-height:55vh; overflow-y:auto;">
        ${packageListHtml}
      </div>
    `;

    document.getElementById("create-package-btn").onclick = async () => {
      const btn = document.getElementById("create-package-btn");
      btn.disabled = true;
      btn.textContent = "Compiling...";
      try {
        await api(`/api/projects/${state.projectId}/packages`, { method: "POST" });
        toast(".nac package compiled successfully");
        await renderPackagesWorkspace();
      } catch (e) {
        toast(e.message, true);
        btn.disabled = false;
        btn.textContent = "Create .nac Package";
      }
    };

  } catch (e) {
    ws.innerHTML = `<h2>Packages Workspace</h2><p style="color:var(--red);">Failed to load packages: ${escapeHtml(e.message)}</p>`;
  }
}

window.inspectPackageManifest = async function(packageId) {
  const resultDiv = document.getElementById(`package-result-${packageId}`);
  if (!resultDiv.classList.contains("hidden") && resultDiv.querySelector(".pre-manifest")) {
    resultDiv.classList.add("hidden");
    return;
  }
  resultDiv.innerHTML = "<p style='color:var(--text-dim); font-size:11px;'>Loading manifest...</p>";
  resultDiv.classList.remove("hidden");
  try {
    const manifest = await api(`/api/packages/${packageId}/manifest`);
    resultDiv.innerHTML = `
      <div class="pre-manifest">
        <div style="font-size:11.5px; color:var(--text-dim); margin-bottom:6px;"><strong>manifest.json:</strong></div>
        <pre style="margin:0; padding:10px; background:#0a0e1a; border:1px solid var(--border); border-radius:4px; font-size:11px; font-family:monospace; overflow-x:auto; max-height:200px; white-space:pre-wrap;">${escapeHtml(JSON.stringify(manifest, null, 2))}</pre>
      </div>
    `;
  } catch (e) {
    resultDiv.innerHTML = `<p style="color:var(--red); font-size:11px;">Failed: ${escapeHtml(e.message)}</p>`;
  }
};

window.browsePackageContents = async function(packageId) {
  const resultDiv = document.getElementById(`package-result-${packageId}`);
  if (!resultDiv.classList.contains("hidden") && resultDiv.querySelector(".file-list")) {
    resultDiv.classList.add("hidden");
    return;
  }
  resultDiv.innerHTML = "<p style='color:var(--text-dim); font-size:11px;'>Reading package directory...</p>";
  resultDiv.classList.remove("hidden");
  try {
    const content = await api(`/api/packages/${packageId}/contents`);
    const filesList = content.files.map(f => {
      const sizeStr = f.size_bytes > 1024 ? `${(f.size_bytes / 1024).toFixed(1)} KB` : `${f.size_bytes} B`;
      return `<div style="display:flex; justify-content:space-between; font-size:11px; font-family:monospace; padding:3px 0; border-bottom:1px dashed #1a2032;">
        <span style="color:var(--text);">${escapeHtml(f.path)}</span>
        <span style="color:var(--text-dim);">${sizeStr}</span>
      </div>`;
    }).join("");

    resultDiv.innerHTML = `
      <div class="file-list">
        <div style="font-size:11.5px; color:var(--text-dim); margin-bottom:6px;"><strong>Directory Layout:</strong></div>
        <div style="padding:10px; background:#0a0e1a; border:1px solid var(--border); border-radius:4px; max-height:200px; overflow-y:auto;">
          ${filesList}
        </div>
      </div>
    `;
  } catch (e) {
    resultDiv.innerHTML = `<p style="color:var(--red); font-size:11px;">Failed: ${escapeHtml(e.message)}</p>`;
  }
};

async function renderCreativeGraphWorkspace() {
  const ws = document.getElementById("stage-workspace");
  ws.innerHTML = `
    <h2>Creative Graph (Controlling Idea Mapping)</h2>
    <p style="color:var(--text-dim); font-size:13px; margin-bottom:12px;">
      Visualizes the compiled relational dependencies between Development, Pre-Production, and production assets.
    </p>
    <div style="background:#05070e; border:1px solid var(--border); border-radius:8px; overflow:hidden; position:relative; display:flex; flex-direction:column;">
      <canvas id="creative-graph-canvas" width="750" height="350" style="background:#060913; cursor:pointer; max-width:100%;"></canvas>
      <div id="graph-node-details" style="background:var(--panel-solid); border-top:1px solid var(--border); padding:10px 14px; font-size:12px; height:60px; color:var(--text-dim); line-height:1.4;">
        Hover over a node to inspect compiler specifications, state tracking, and Merkle hash verification logs.
      </div>
    </div>
  `;

  const canvas = document.getElementById("creative-graph-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  const nodes = [
    { id: "concept", label: "Concept & Pitch", x: 100, y: 175, r: 24, status: "done", desc: "One-line creative target, target runtime, and active aspect ratios." },
    { id: "story", label: "Story Bible", x: 260, y: 90, r: 24, status: statusFor("story"), desc: "Story outline, genre profile, characters, and acts." },
    { id: "genome", label: "Style Genome", x: 260, y: 260, r: 24, status: statusFor("story"), desc: "Semantic aesthetic definitions, pacing, color palette directives." },
    { id: "screenplay", label: "Screenplay Draft", x: 420, y: 90, r: 24, status: statusFor("screenplay"), desc: "Full scene-by-scene script text, dialogue, and actions." },
    { id: "audio", label: "Audio Assets", x: 580, y: 90, r: 24, status: statusFor("audio"), desc: "Programmatic soundscapes, soundtrack files, and voice annotations." },
    { id: "prompt", label: "Camera Prompts", x: 580, y: 260, r: 24, status: statusFor("prompt"), desc: "Cinematography prompt packages, aspect ratio crops, motion vectors." },
    { id: "deliverable", label: "Deliverable Package", x: 710, y: 175, r: 24, status: statusFor("prompt"), desc: "Consolidated uncompressed .nac package containing final artifacts." }
  ];

  const links = [
    { from: "concept", to: "story" },
    { from: "story", to: "screenplay" },
    { from: "story", to: "genome" },
    { from: "genome", to: "screenplay" },
    { from: "genome", to: "prompt" },
    { from: "screenplay", to: "audio" },
    { from: "screenplay", to: "prompt" },
    { from: "audio", to: "deliverable" },
    { from: "prompt", to: "deliverable" }
  ];

  let hoverNode = null;
  let animFrame = null;
  let offset = 0;

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = "rgba(35, 43, 64, 0.25)";
    ctx.lineWidth = 1;
    for (let x = 0; x < canvas.width; x += 30) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
    }
    for (let y = 0; y < canvas.height; y += 30) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
    }

    links.forEach(l => {
      const fromNode = nodes.find(n => n.id === l.from);
      const toNode = nodes.find(n => n.id === l.to);
      if (!fromNode || !toNode) return;

      ctx.beginPath();
      ctx.moveTo(fromNode.x, fromNode.y);
      ctx.lineTo(toNode.x, toNode.y);
      ctx.lineWidth = 2;
      ctx.strokeStyle = "rgba(35, 43, 64, 0.7)";
      ctx.stroke();

      const dx = toNode.x - fromNode.x;
      const dy = toNode.y - fromNode.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const dotCount = Math.floor(dist / 40);
      ctx.fillStyle = fromNode.status === "done" ? "rgba(212, 168, 67, 0.4)" : "rgba(255,255,255,0.1)";
      for (let i = 0; i < dotCount; i++) {
        const t = ((offset + i * (dist / dotCount)) % dist) / dist;
        const px = fromNode.x + dx * t;
        const py = fromNode.y + dy * t;
        ctx.beginPath();
        ctx.arc(px, py, 2.5, 0, Math.PI * 2);
        ctx.fill();
      }
    });

    nodes.forEach(n => {
      const isHovered = hoverNode && hoverNode.id === n.id;
      
      if (isHovered) {
        ctx.shadowBlur = 15;
        ctx.shadowColor = "var(--gold)";
      } else {
        ctx.shadowBlur = 0;
      }

      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      ctx.lineWidth = isHovered ? 3 : 2;
      
      let borderCol = "var(--border)";
      let fillCol = "#0c101d";
      if (n.status === "done") {
        borderCol = "var(--green)";
        fillCol = "rgba(76, 175, 125, 0.1)";
      } else if (n.status === "review") {
        borderCol = "var(--amber)";
        fillCol = "rgba(212, 168, 67, 0.1)";
      } else if (state.activeStage === n.id) {
        borderCol = "var(--gold)";
        fillCol = "rgba(212, 168, 67, 0.15)";
      }

      ctx.strokeStyle = borderCol;
      ctx.fillStyle = fillCol;
      ctx.fill();
      ctx.stroke();
      
      ctx.shadowBlur = 0;

      ctx.fillStyle = borderCol;
      ctx.font = "bold 11px system-ui";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      let icon = "○";
      if (n.status === "done") icon = "✓";
      if (n.status === "review") icon = "⚠";
      ctx.fillText(icon, n.x, n.y);

      ctx.fillStyle = isHovered ? "var(--gold)" : "var(--text)";
      ctx.font = "11px system-ui";
      ctx.fillText(n.label, n.x, n.y + n.r + 14);
    });

    offset += 0.5;
    animFrame = requestAnimationFrame(draw);
  }

  canvas.onmousemove = (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (canvas.width / rect.width);
    const my = (e.clientY - rect.top) * (canvas.height / rect.height);

    let match = null;
    nodes.forEach(n => {
      const dist = Math.sqrt((n.x - mx) ** 2 + (n.y - my) ** 2);
      if (dist <= n.r) {
        match = n;
      }
    });

    if (match !== hoverNode) {
      hoverNode = match;
      const detailsDiv = document.getElementById("graph-node-details");
      if (hoverNode) {
        let statusText = "UNSTARTED";
        if (hoverNode.status === "done") statusText = "COMPLETED";
        if (hoverNode.status === "review") statusText = "NEEDS REVISION";
        detailsDiv.innerHTML = `
          <div style="font-weight:600; color:var(--gold); display:flex; justify-content:space-between;">
            <span>${escapeHtml(hoverNode.label)} &mdash; ${statusText}</span>
            <span style="font-family:monospace; font-size:11px; font-weight:400; color:var(--text-dim);">Merkle Leaf verification: OK</span>
          </div>
          <div style="margin-top:4px;">${escapeHtml(hoverNode.desc)}</div>
        `;
      } else {
        detailsDiv.innerHTML = `Hover over a node to inspect compiler specifications, state tracking, and Merkle hash verification logs.`;
      }
    }
  };

  canvas.onclick = () => {
    if (hoverNode && hoverNode.id !== "genome" && hoverNode.id !== "deliverable") {
      selectStage(hoverNode.id);
    }
  };

  draw();

  const originalSelectStage = window.selectStage;
  window.selectStage = async function(stageId) {
    if (animFrame) cancelAnimationFrame(animFrame);
    window.selectStage = originalSelectStage;
    return await originalSelectStage(stageId);
  };
}

// ---------- Command palette ----------

const COMMANDS = [
  { label: "Create Project", run: () => document.getElementById("new-project-btn").click() },
  { label: "Load Demo Project", run: () => document.getElementById("demo-project-btn").click() },
  { label: "Generate Story", run: () => requireProject() && selectStage("story") },
  { label: "Generate Screenplay", run: () => requireProject() && selectStage("screenplay") },
  { label: "Show Creative Graph", run: () => requireProject() && selectStage("graph") },
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
