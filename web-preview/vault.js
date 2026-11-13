/* OmniForge Vault — Obsidian-style knowledge graph.
 *
 * Nodes are built from the real data.js exports (18 skills, 10 MCP tools,
 * their categories). The layout is a small force simulation: repulsion between
 * all nodes, spring attraction along edges, and gentle centring. Nothing is
 * hardcoded; change data.js and the vault changes with it.
 */
import {SKILLS, MCP_TOOLS, META} from "./data.js";

// ------------------------------------------------------------------ model

const KIND = {skill: "skill", adapter: "adapter", tool: "tool", category: "category"};

/** Build nodes + edges once, from the data. */
function buildGraph() {
  const nodes = new Map();   // id -> node
  const edges = [];          // {source, target}

  const add = (id, label, kind, payload) => {
    if (nodes.has(id)) return nodes.get(id);
    const node = {id, label, kind, payload, x: 0, y: 0, vx: 0, vy: 0, r: 7};
    nodes.set(id, node);
    return node;
  };
  const link = (a, b) => {
    if (a === b) return;
    if (edges.some(e => (e.source === a && e.target === b) || (e.source === b && e.target === a))) return;
    edges.push({source: a, target: b});
  };

  // categories first, so skills can attach to them
  const categories = [...new Set(SKILLS.map(s => s.category))].sort();
  for (const cat of categories) {
    add(`cat:${cat}`, cat, KIND.category, {category: cat});
  }

  for (const skill of SKILLS) {
    const kind = skill.type === "adapter" ? KIND.adapter : KIND.skill;
    add(`skill:${skill.name}`, skill.name, kind, skill);
    link(`skill:${skill.name}`, `cat:${skill.category}`);
  }

  for (const tool of MCP_TOOLS) {
    add(`tool:${tool.name}`, tool.name.replace(/^omniforge_/, ""), KIND.tool, tool);
  }

  // Semantic links: a tool that mentions a skill's subject shares an edge.
  // This is a readable heuristic, not a claim of a formal dependency graph.
  const toolToSkills = {
    omniforge_search: ["repo-recon", "python-symbols"],
    omniforge_load: ["repo-recon"],
    omniforge_run: ["firmware-preflight", "python-symbols", "log-triage"],
    omniforge_browser: ["browser-snapshot", "visual-qa"],
    omniforge_chain_verify: ["git-diff-review", "secret-hygiene"],
    omniforge_chain_proof: ["git-diff-review"],
    omniforge_provenance_verify: ["git-diff-review", "secret-hygiene"],
    omniforge_provenance_proof: ["git-diff-review"],
    omniforge_provenance_audit: ["git-diff-review", "secret-hygiene", "visual-qa"],
    omniforge_budget: ["repo-recon", "dependency-inventory"],
  };
  for (const [tool, skills] of Object.entries(toolToSkills)) {
    for (const skill of skills) {
      if (nodes.has(`tool:${tool}`) && nodes.has(`skill:${skill}`)) {
        link(`tool:${tool}`, `skill:${skill}`);
      }
    }
  }

  return {nodes: [...nodes.values()], edges};
}

const graph = buildGraph();
const byId = new Map(graph.nodes.map(n => [n.id, n]));

// ------------------------------------------------------------------ canvas

const canvas = document.getElementById("graphCanvas");
const ctx = canvas.getContext("2d");
const wrap = document.getElementById("graphWrap");

let width = 0, height = 0, dpr = 1;
let transform = {x: 0, y: 0, k: 1};
let selectedId = null;
let hoveredId = null;
let physicsOn = true;
let alpha = 1;

function resize() {
  dpr = Math.min(window.devicePixelRatio || 1, 2);
  const rect = wrap.getBoundingClientRect();
  width = rect.width;
  height = rect.height;
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  seedPositions();
}

/** Place nodes on a spiral so the first frames are not a single blob. */
function seedPositions() {
  const cx = width / 2, cy = height / 2;
  const radius = Math.min(width, height) * 0.36;
  graph.nodes.forEach((node, i) => {
    const angle = (i / graph.nodes.length) * Math.PI * 2 * 3;
    const r = radius * (0.35 + 0.65 * (i / graph.nodes.length));
    node.x = cx + Math.cos(angle) * r;
    node.y = cy + Math.sin(angle) * r;
    node.vx = 0;
    node.vy = 0;
  });
  alpha = 1;
}

// ------------------------------------------------------------------ physics

const CHARGE = -320;        // repulsion
const SPRING = 0.012;       // edge stiffness
const SPRING_LEN = 96;      // rest length
const CENTRE = 0.006;
const DAMPING = 0.86;

function stepPhysics() {
  if (!physicsOn || alpha < 0.005) return;
  alpha *= 0.985;

  // repulsion (O(n^2) is fine for ~40 nodes)
  for (let i = 0; i < graph.nodes.length; i++) {
    const a = graph.nodes[i];
    for (let j = i + 1; j < graph.nodes.length; j++) {
      const b = graph.nodes[j];
      let dx = b.x - a.x, dy = b.y - a.y;
      let d2 = dx * dx + dy * dy;
      if (d2 < 1) { dx = Math.random() - 0.5; dy = Math.random() - 0.5; d2 = 1; }
      const force = (CHARGE * alpha) / d2;
      const d = Math.sqrt(d2);
      const fx = (dx / d) * force, fy = (dy / d) * force;
      a.vx += fx; a.vy += fy;
      b.vx -= fx; b.vy -= fy;
    }
  }

  // springs
  for (const edge of graph.edges) {
    const a = byId.get(edge.source), b = byId.get(edge.target);
    if (!a || !b) continue;
    const dx = b.x - a.x, dy = b.y - a.y;
    const d = Math.max(1, Math.hypot(dx, dy));
    const force = (d - SPRING_LEN) * SPRING * alpha;
    const fx = (dx / d) * force, fy = (dy / d) * force;
    a.vx += fx; a.vy += fy;
    b.vx -= fx; b.vy -= fy;
  }

  // centring + integrate
  const cx = width / 2, cy = height / 2;
  for (const node of graph.nodes) {
    node.vx += (cx - node.x) * CENTRE * alpha;
    node.vy += (cy - node.y) * CENTRE * alpha;
    node.vx *= DAMPING;
    node.vy *= DAMPING;
    node.x += node.vx;
    node.y += node.vy;
  }
}

// ------------------------------------------------------------------ colours

function colourOf(kind) {
  switch (kind) {
    case KIND.adapter: return "#e0a171";
    case KIND.tool: return "#c9a26e";
    case KIND.category: return "#6f8c7b";
    default: return "#8fb59c";
  }
}
function radiusOf(node) {
  switch (node.kind) {
    case KIND.category: return 9;
    case KIND.tool: return 6.5;
    default: return 7;
  }
}

// ------------------------------------------------------------------ drawing

function draw() {
  ctx.clearRect(0, 0, width, height);
  ctx.save();
  ctx.translate(transform.x, transform.y);
  ctx.scale(transform.k, transform.k);

  const connected = new Set();
  if (selectedId) {
    connected.add(selectedId);
    for (const e of graph.edges) {
      if (e.source === selectedId) connected.add(e.target);
      if (e.target === selectedId) connected.add(e.source);
    }
  }

  // edges
  for (const edge of graph.edges) {
    const a = byId.get(edge.source), b = byId.get(edge.target);
    if (!a || !b) continue;
    const isHot = selectedId && (edge.source === selectedId || edge.target === selectedId);
    const isHover = hoveredId && (edge.source === hoveredId || edge.target === hoveredId);
    const dim = selectedId && !isHot;

    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    if (isHot) {
      ctx.strokeStyle = "rgba(224,161,113,0.55)";
      ctx.lineWidth = 1.6;
    } else if (isHover) {
      ctx.strokeStyle = "rgba(143,181,156,0.4)";
      ctx.lineWidth = 1.2;
    } else {
      ctx.strokeStyle = dim ? "rgba(80,90,82,0.10)" : "rgba(90,102,92,0.28)";
      ctx.lineWidth = 1;
    }
    ctx.stroke();

    // travelling pulse along selected edges
    if (isHot) {
      const t = (performance.now() / 1400) % 1;
      const px = a.x + (b.x - a.x) * t;
      const py = a.y + (b.y - a.y) * t;
      ctx.beginPath();
      ctx.arc(px, py, 2.2, 0, Math.PI * 2);
      ctx.fillStyle = "#f0c69c";
      ctx.fill();
    }
  }

  // nodes
  for (const node of graph.nodes) {
    const r = radiusOf(node);
    const isSelected = node.id === selectedId;
    const isHover = node.id === hoveredId;
    const dim = selectedId && !connected.has(node.id);
    const colour = colourOf(node.kind);

    if (isSelected) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 6, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(224,161,113,0.16)";
      ctx.fill();
    }

    ctx.beginPath();
    ctx.arc(node.x, node.y, isSelected ? r + 1.5 : (isHover ? r + 1 : r), 0, Math.PI * 2);
    ctx.fillStyle = dim ? "rgba(70,78,71,0.5)" : colour;
    ctx.fill();

    if (node.kind === KIND.category && !dim) {
      ctx.strokeStyle = "rgba(111,140,123,0.6)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 3.5, 0, Math.PI * 2);
      ctx.stroke();
    }

    // labels: always for categories and selection, otherwise when zoomed in
    const showLabel = node.kind === KIND.category || isSelected || isHover || transform.k > 1.15;
    if (showLabel && !dim) {
      ctx.font = `${node.kind === KIND.category ? "600 10px" : "500 9.5px"} ui-monospace, monospace`;
      ctx.fillStyle = isSelected ? "#f3e3d2" : (isHover ? "#dfe5dc" : "rgba(190,200,190,0.72)");
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillText(node.label, node.x, node.y + r + 5);
    }
  }

  ctx.restore();
}

// ------------------------------------------------------------------ loop

let rafId = null;
function frame() {
  stepPhysics();
  draw();
  rafId = requestAnimationFrame(frame);
}

// ------------------------------------------------------------------ interaction

function toWorld(clientX, clientY) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (clientX - rect.left - transform.x) / transform.k,
    y: (clientY - rect.top - transform.y) / transform.k,
  };
}

function nodeAt(wx, wy) {
  let best = null, bestD = Infinity;
  for (const node of graph.nodes) {
    const d = Math.hypot(node.x - wx, node.y - wy);
    const hit = radiusOf(node) + 9 / transform.k;
    if (d < hit && d < bestD) { best = node; bestD = d; }
  }
  return best;
}

let dragging = null;
let panning = null;

canvas.addEventListener("pointerdown", event => {
  const world = toWorld(event.clientX, event.clientY);
  const hit = nodeAt(world.x, world.y);
  canvas.setPointerCapture(event.pointerId);
  if (hit) {
    dragging = {node: hit, offsetX: hit.x - world.x, offsetY: hit.y - world.y};
    hit.vx = 0; hit.vy = 0;
    alpha = Math.max(alpha, 0.35);
    canvas.classList.add("dragging");
  } else {
    panning = {startX: event.clientX, startY: event.clientY, ox: transform.x, oy: transform.y};
  }
});

canvas.addEventListener("pointermove", event => {
  const world = toWorld(event.clientX, event.clientY);
  if (dragging) {
    dragging.node.x = world.x + dragging.offsetX;
    dragging.node.y = world.y + dragging.offsetY;
    dragging.node.vx = 0; dragging.node.vy = 0;
    return;
  }
  if (panning) {
    transform.x = panning.ox + (event.clientX - panning.startX);
    transform.y = panning.oy + (event.clientY - panning.startY);
    return;
  }
  const hit = nodeAt(world.x, world.y);
  const next = hit ? hit.id : null;
  if (next !== hoveredId) {
    hoveredId = next;
    canvas.style.cursor = hit ? "pointer" : "grab";
  }
});

canvas.addEventListener("pointerup", event => {
  if (dragging) {
    const moved = Math.hypot(dragging.node.vx, dragging.node.vy);
    selectNode(dragging.node.id);
    dragging = null;
    canvas.classList.remove("dragging");
  } else if (panning) {
    panning = null;
  }
  canvas.releasePointerCapture(event.pointerId);
});

canvas.addEventListener("pointercancel", () => {
  dragging = null; panning = null;
  canvas.classList.remove("dragging");
});

canvas.addEventListener("click", event => {
  const world = toWorld(event.clientX, event.clientY);
  const hit = nodeAt(world.x, world.y);
  if (hit) selectNode(hit.id);
});

canvas.addEventListener("wheel", event => {
  event.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const mx = event.clientX - rect.left;
  const my = event.clientY - rect.top;
  const factor = event.deltaY < 0 ? 1.1 : 0.9;
  const nextK = Math.min(3.2, Math.max(0.35, transform.k * factor));
  const ratio = nextK / transform.k;
  transform.x = mx - (mx - transform.x) * ratio;
  transform.y = my - (my - transform.y) * ratio;
  transform.k = nextK;
}, {passive: false});

// ------------------------------------------------------------------ note panel

const noteEmpty = document.getElementById("noteEmpty");
const noteBody = document.getElementById("noteBody");
const noteBadges = document.getElementById("noteBadges");
const noteTitle = document.getElementById("noteTitle");
const noteDesc = document.getElementById("noteDesc");
const noteMeta = document.getElementById("noteMeta");
const noteMetaSection = document.getElementById("noteMetaSection");
const noteLinks = document.getElementById("noteLinks");
const noteLinksSection = document.getElementById("noteLinksSection");
const noteLinkCount = document.getElementById("noteLinkCount");
const noteCmd = document.getElementById("noteCmd");
const noteCmdSection = document.getElementById("noteCmdSection");

const escapeHtml = v => String(v)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;");

function neighboursOf(id) {
  const out = [];
  for (const edge of graph.edges) {
    if (edge.source === id) out.push(edge.target);
    else if (edge.target === id) out.push(edge.source);
  }
  return out;
}

function selectNode(id) {
  selectedId = id;
  const node = byId.get(id);
  if (!node) return;

  noteEmpty.hidden = true;
  noteBody.hidden = false;

  const badge = (text, cls) => `<span class="note-badge ${cls}">${escapeHtml(text)}</span>`;
  const kindBadge = {
    [KIND.skill]: badge("BUNDLED SKILL", "nb-skill"),
    [KIND.adapter]: badge("ADAPTER", "nb-adapter"),
    [KIND.tool]: badge("MCP TOOL", "nb-tool"),
    [KIND.category]: badge("CATEGORY", "nb-cat"),
  }[node.kind];
  noteBadges.innerHTML = kindBadge || "";

  noteTitle.textContent = node.kind === KIND.tool ? node.payload.name : node.label;

  const rows = [];
  if (node.kind === KIND.skill || node.kind === KIND.adapter) {
    noteDesc.textContent = node.payload.description || "";
    rows.push(["Kategori", node.payload.category]);
    rows.push(["Keperluan", node.payload.need]);
    rows.push(["Jenis", node.payload.type === "adapter" ? "adapter (alat luar)" : "skrip terbina"]);
    noteCmd.textContent = node.payload.example || `omniforge load ${node.payload.name}`;
    noteCmdSection.hidden = false;
  } else if (node.kind === KIND.tool) {
    noteDesc.textContent = node.payload.description || "";
    rows.push(["Akses", node.payload.type]);
    rows.push(["Argumen wajib", (node.payload.required || []).join(", ") || "tiada"]);
    noteCmd.textContent = JSON.stringify(
      {tool: node.payload.name, arguments: node.payload.args || {}}, null, 2);
    noteCmdSection.hidden = false;
  } else {
    const members = graph.nodes.filter(n =>
      n.kind !== KIND.category && n.payload.category === node.payload.category);
    noteDesc.textContent = `${members.length} skill dalam kategori ${node.payload.category}.`;
    rows.push(["Ahli", members.map(m => m.label).join(", ")]);
    noteCmdSection.hidden = true;
  }

  noteMeta.innerHTML = rows
    .map(([k, v]) => `<dt>${escapeHtml(k)}</dt><dd>${escapeHtml(v ?? "—")}</dd>`)
    .join("");
  noteMetaSection.hidden = rows.length === 0;

  const neighbours = neighboursOf(id);
  noteLinkCount.textContent = neighbours.length ? `(${neighbours.length})` : "";
  noteLinks.innerHTML = neighbours.map(nid => {
    const other = byId.get(nid);
    const dot = colourOf(other.kind);
    return `<button class="note-link" data-target="${escapeHtml(nid)}">`
      + `<span class="nl-dot" style="background:${dot}"></span>${escapeHtml(other.label)}</button>`;
  }).join("");
  noteLinksSection.hidden = neighbours.length === 0;
}

noteLinks.addEventListener("click", event => {
  const button = event.target.closest("[data-target]");
  if (button) selectNode(button.dataset.target);
});

document.getElementById("noteClose").addEventListener("click", () => {
  selectedId = null;
  noteBody.hidden = true;
  noteEmpty.hidden = false;
});

// ------------------------------------------------------------------ controls

document.getElementById("btnReheat").addEventListener("click", () => {
  seedPositions();
  hideHint();
});
document.getElementById("btnPause").addEventListener("click", event => {
  physicsOn = !physicsOn;
  event.currentTarget.classList.toggle("on", !physicsOn);
  event.currentTarget.textContent = physicsOn ? "⏸ Fizik" : "▶ Fizik";
});

const hint = document.getElementById("graphHint");
let hintTimer = setTimeout(hideHint, 7000);
function hideHint() { hint.classList.add("fade"); clearTimeout(hintTimer); }
canvas.addEventListener("pointerdown", hideHint, {once: true});

// ------------------------------------------------------------------ list mode

const listView = document.getElementById("listView");
const graphWrap = document.getElementById("graphWrap");
const notePanel = document.getElementById("notePanel");
const listGroups = document.getElementById("listGroups");
const listCount = document.getElementById("listCount");

function renderList() {
  const groups = [
    ["Skill terbina", SKILLS.filter(s => s.type === "builtin")],
    ["Adapter (alat luar)", SKILLS.filter(s => s.type === "adapter")],
    ["MCP tool", MCP_TOOLS.map(t => ({
      name: t.name, description: t.description, category: "MCP",
    }))],
  ];
  listGroups.innerHTML = groups.map(([title, items]) => `
    <section class="list-group">
      <h2>${escapeHtml(title)} · ${items.length}</h2>
      <div class="list-cards">
        ${items.map(item => `
          <button class="list-card" data-open="${escapeHtml(
            item.name.startsWith("omniforge_") ? `tool:${item.name}` : `skill:${item.name}`
          )}">
            <strong>${escapeHtml(item.name)}</strong>
            <small>${escapeHtml((item.description || "").slice(0, 96))}${(item.description || "").length > 96 ? "…" : ""}</small>
          </button>`).join("")}
      </div>
    </section>`).join("");
  listCount.textContent = `(${SKILLS.length + MCP_TOOLS.length})`;
}

listGroups.addEventListener("click", event => {
  const card = event.target.closest("[data-open]");
  if (!card) return;
  const id = card.dataset.open;
  setMode("graph");
  selectNode(id);
  const node = byId.get(id);
  if (node) {
    transform.k = Math.max(transform.k, 1.3);
    transform.x = width / 2 - node.x * transform.k;
    transform.y = height / 2 - node.y * transform.k;
  }
});

function setMode(mode) {
  const isGraph = mode === "graph";
  graphWrap.hidden = !isGraph;
  notePanel.hidden = !isGraph;
  listView.hidden = isGraph;
  document.querySelectorAll(".vault-tab").forEach(tab => {
    tab.classList.toggle("active", tab.dataset.mode === mode);
  });
  if (isGraph) resize();
}

document.querySelectorAll(".vault-tab").forEach(tab => {
  tab.addEventListener("click", () => setMode(tab.dataset.mode));
});

// ------------------------------------------------------------------ search

const searchInput = document.getElementById("vaultSearch");

function matches(node, query) {
  if (!query) return true;
  const hay = `${node.label} ${node.payload.description || ""} ${node.payload.category || ""}`.toLowerCase();
  return query.split(/\s+/).filter(Boolean).some(term => hay.includes(term));
}

searchInput.addEventListener("input", () => {
  const query = searchInput.value.trim().toLowerCase();
  if (!query) {
    graph.nodes.forEach(n => { n.hidden = false; });
    return;
  }
  const hits = graph.nodes.filter(n => matches(n, query));
  // Focus the first hit so search is useful without hunting in the graph.
  if (hits.length && document.activeElement === searchInput) {
    const first = hits[0];
    transform.k = Math.max(transform.k, 1.2);
    transform.x = width / 2 - first.x * transform.k;
    transform.y = height / 2 - first.y * transform.k;
  }
});

document.addEventListener("keydown", event => {
  if (event.key === "/" && document.activeElement !== searchInput) {
    event.preventDefault();
    searchInput.focus();
  }
  if (event.key === "Escape") {
    searchInput.blur();
    selectedId = null;
    noteBody.hidden = true;
    noteEmpty.hidden = false;
  }
});

// ------------------------------------------------------------------ boot

function boot() {
  resize();
  renderList();
  document.getElementById("graphCount").textContent = `${graph.nodes.length} nod · ${graph.edges.length} pautan`;
  const builtin = SKILLS.filter(s => s.type === "builtin").length;
  const adapters = SKILLS.filter(s => s.type === "adapter").length;
  document.getElementById("vaultStats").textContent =
    `v${META.version} · ${SKILLS.length} skill (${builtin} terbina, ${adapters} adapter) · ${MCP_TOOLS.length} tool`;
  frame();
  // The graph settles in a couple of seconds; stop burning frames after that.
  setTimeout(() => { physicsOn = false; }, 4200);
}

window.addEventListener("resize", () => { resize(); });
boot();
