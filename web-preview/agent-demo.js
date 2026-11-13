/* Agent Demo — one prompt drives real GitHub API calls and the real CLI.
 *
 * Honest boundaries:
 *  - The GitHub figures come from the public API (no token, CORS enabled).
 *    Unauthenticated rate limit is 60 requests/hour.
 *  - The CLI runs on the local /api/terminal endpoint, which enforces its own
 *    allowlist and destroys the project after each request.
 *  - There is NO language model here. The "plan" is a deterministic keyword
 *    router over the prompt, and the page says so. It does not pretend to be
 *    DeepSeek or any other model.
 */
(function () {
  "use strict";

  const REPO = "muhdmunir961-byte/omniforge";
  const API = "https://api.github.com";
  const CLI = "/api/terminal";

  const $ = id => document.getElementById(id);
  const statusEl = $("agentStatus");
  const statusText = $("statusText");
  const runBtn = $("runBtn");
  const promptInput = $("promptInput");
  const pipeline = $("pipeline");
  const phaseList = $("phaseList");
  const progressBar = $("progressBar");
  const liveGrid = $("liveGrid");
  const logStream = $("logStream");
  const logMeta = $("logMeta");
  const cliOut = $("cliOut");
  const cliMeta = $("cliMeta");
  const resultBody = $("resultBody");
  const resultMeta = $("resultMeta");
  const ghMeta = $("ghMeta");

  let running = false;
  const started = Date.now();

  // ---------------------------------------------------------------- ui bits

  function setStatus(text, state) {
    statusText.textContent = text;
    statusEl.dataset.state = state || "idle";
  }

  function stamp() {
    const s = ((Date.now() - started) / 1000).toFixed(1);
    return `+${s}s`;
  }

  function log(text, cls) {
    const line = document.createElement("div");
    line.className = "log-line";
    const t = document.createElement("span");
    t.className = "t";
    t.textContent = stamp() + " ";
    const body = document.createElement("span");
    if (cls) body.className = cls;
    body.textContent = text;
    line.append(t, body);
    logStream.appendChild(line);
    logStream.scrollTop = logStream.scrollHeight;
    logMeta.textContent = `${logStream.children.length} baris`;
  }

  function escapeHtml(v) {
    return String(v).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function pause(ms) { return new Promise(r => setTimeout(r, ms)); }

  // ---------------------------------------------------------------- phases

  const PHASES = [
    { id: "plan", label: "Faham prompt" },
    { id: "repo", label: "GitHub API" },
    { id: "checks", label: "Status CI" },
    { id: "cli", label: "CLI sebenar" },
    { id: "report", label: "Laporan" },
  ];

  function renderPhases() {
    phaseList.innerHTML = PHASES.map((p, i) =>
      `<li class="phase" data-phase="${p.id}" style="animation-delay:${i * 60}ms">
         <span class="phase-dot"></span><span>${escapeHtml(p.label)}</span>
       </li>`).join("");
  }

  function setPhase(id, state) {
    const el = phaseList.querySelector(`[data-phase="${id}"]`);
    if (!el) return;
    el.classList.toggle("active", state === "active");
    el.classList.toggle("done", state === "done");
  }

  function setProgress(fraction) {
    progressBar.style.width = Math.round(fraction * 100) + "%";
  }

  // ---------------------------------------------------------------- github

  async function gh(path) {
    const response = await fetch(`${API}/repos/${REPO}${path}`, {
      headers: { Accept: "application/vnd.github+json" },
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`GitHub API ${response.status} untuk ${path || "/"}`);
    }
    const remaining = response.headers.get("x-ratelimit-remaining");
    if (remaining !== null) ghMeta.textContent = `kuota ${remaining}`;
    return response.json();
  }

  function renderRepo(repo) {
    $("ghName").textContent = repo.full_name;
    $("ghDesc").textContent = repo.description || "";
    const stats = [
      ["BINTANG", repo.stargazers_count],
      ["FORK", repo.forks_count],
      ["ISU", repo.open_issues_count],
      ["BAHASA", repo.language || "—"],
    ];
    $("ghStats").innerHTML = stats.map(([k, v], i) =>
      `<div class="gh-stat" data-i="${i}"><span>${k}</span><strong>${escapeHtml(v)}</strong></div>`
    ).join("");
    requestAnimationFrame(() => {
      $("ghStats").querySelectorAll(".gh-stat").forEach((el, i) => {
        setTimeout(() => {
          el.classList.add("bump");
          setTimeout(() => el.classList.remove("bump"), 450);
        }, i * 90);
      });
    });
  }

  function renderChecks(runs) {
    if (!runs.length) {
      $("ghChecks").innerHTML = `<span class="chk chk-bad">TIADA CHECK</span>`;
      return;
    }
    $("ghChecks").innerHTML = runs.slice(0, 12).map((run, i) => {
      const ok = run.conclusion === "success";
      const cls = ok ? "chk-ok" : "chk-bad";
      const label = ok ? "✓" : (run.conclusion === null ? "…" : "✕");
      return `<span class="chk ${cls}" style="animation-delay:${i * 45}ms">${label} ${escapeHtml(run.name.slice(0, 22))}</span>`;
    }).join("");
  }

  function renderCommits(commits) {
    $("ghCommits").innerHTML = commits.slice(0, 5).map((c, i) =>
      `<div class="commit" style="animation-delay:${i * 55}ms">
         <b>${escapeHtml(c.sha.slice(0, 7))}</b>
         <span>${escapeHtml(c.commit.message.split("\n")[0].slice(0, 62))}</span>
       </div>`).join("");
  }

  // ---------------------------------------------------------------- cli

  async function cli(commands) {
    const response = await fetch(CLI, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ commands }),
      cache: "no-store",
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "CLI menolak arahan");
    return (data.results || []).map(r => {
      let parsed = null;
      try { parsed = JSON.parse(r.stdout); } catch (_) { /* raw */ }
      return { ...r, parsed: parsed && typeof parsed === "object" ? parsed : null };
    });
  }

  function showCli(payload, meta) {
    const pretty = typeof payload === "string" ? payload : JSON.stringify(payload, null, 2);
    cliOut.innerHTML = escapeHtml(pretty)
      .replace(/"([^"]+)":/g, '<span class="k">"$1"</span>:')
      .replace(/"ok": (true)/g, '"ok": <span class="ok">true</span>');
    cliMeta.textContent = meta || "";
  }

  // ---------------------------------------------------------------- planning

  /**
   * Deterministic keyword router. This is deliberately NOT a language model:
   * it maps prompt keywords to a fixed plan, and the UI states that plainly.
   */
  function plan(prompt) {
    const q = prompt.toLowerCase();
    const wants = {
      security: /audit|keselamatan|security|secret|kredensial|credential/.test(q),
      ci: /ci|check|status|commit|build|workflow/.test(q),
      chain: /rantai|chain|provenance|integriti|integrity|hash|blockchain/.test(q),
      skills: /skill|kemahiran|pilih|senarai|list|debug/.test(q),
    };
    if (!Object.values(wants).some(Boolean)) wants.skills = true;
    const commands = ["omniforge doctor"];
    if (wants.skills) commands.push("omniforge list");
    if (wants.security) commands.push('omniforge search "security secret"');
    if (wants.ci) commands.push("omniforge integrations doctor");
    if (wants.chain) {
      commands.length = Math.min(commands.length, 2);
      commands.push("ofprov init");
      commands.push("ofprov snapshot");
    }
    return { wants, commands: commands.slice(0, 4) };
  }

  function addResult(mark, title, detail, cls) {
    const item = document.createElement("div");
    item.className = "result-item";
    item.innerHTML = `<span class="ri-mark ${cls || ""}">${mark}</span>
      <div><strong>${escapeHtml(title)}</strong><small>${escapeHtml(detail)}</small></div>`;
    resultBody.appendChild(item);
  }

  // ---------------------------------------------------------------- run

  async function run() {
    if (running) return;
    const prompt = promptInput.value.trim();
    if (!prompt) {
      promptInput.focus();
      return;
    }
    running = true;
    runBtn.disabled = true;
    logStream.innerHTML = "";
    resultBody.innerHTML = "";
    cliOut.innerHTML = '<span class="dim">$ menunggu…</span>';
    pipeline.hidden = false;
    liveGrid.hidden = false;
    renderPhases();
    setProgress(0);
    setStatus("BERJALAN", "running");
    logMeta.textContent = "—";
    cliMeta.textContent = "—";
    resultMeta.textContent = "—";

    log(`prompt: "${prompt}"`, "cmd");
    await pause(180);

    // ---- phase 1: plan
    setPhase("plan", "active");
    setProgress(0.1);
    log("merancang langkah…", "dim");
    const thePlan = plan(prompt);
    await pause(420);
    const wanted = Object.entries(thePlan.wants).filter(([, v]) => v).map(([k]) => k);
    log(`pelan: ${wanted.join(", ") || "umum"}`, "dim");
    log(`arahan CLI: ${thePlan.commands.length}`, "dim");
    setPhase("plan", "done");
    setProgress(0.22);

    // ---- phase 2: repo
    setPhase("repo", "active");
    log("GET /repos/" + REPO, "cmd");
    try {
      const repo = await gh("");
      renderRepo(repo);
      log(`repo: ${repo.full_name} · ${repo.stargazers_count}★ · ${repo.open_issues_count} isu`, "ok");
      addResult("✓", "Repositori dibaca", `${repo.full_name} — ${repo.stargazers_count} bintang, ${repo.forks_count} fork`);
    } catch (error) {
      log(error.message, "err");
      addResult("✕", "GitHub API gagal", error.message, "bad");
    }
    setPhase("repo", "done");
    setProgress(0.44);

    // ---- phase 3: checks
    setPhase("checks", "active");
    log("GET /commits?per_page=5", "cmd");
    try {
      const commits = await gh("/commits?per_page=5");
      renderCommits(commits);
      log(`${commits.length} commit terkini`, "ok");
      if (commits.length) {
        log(`GET /commits/${commits[0].sha.slice(0, 7)}/check-runs`, "cmd");
        const checks = await gh(`/commits/${commits[0].sha}/check-runs?per_page=100`);
        const runs = checks.check_runs || [];
        const failed = runs.filter(r => r.conclusion && !["success", "neutral", "skipped"].includes(r.conclusion));
        renderChecks(runs);
        log(`check-runs: ${runs.length} jumlah, ${failed.length} gagal`,
            failed.length ? "warn" : "ok");
        addResult(failed.length ? "!" : "✓",
          failed.length ? `${failed.length} check gagal` : "Semua check lulus",
          `${runs.length} check-run pada commit ${commits[0].sha.slice(0, 7)}`,
          failed.length ? "warn" : "");
      }
    } catch (error) {
      log(error.message, "err");
      addResult("✕", "Status CI gagal", error.message, "bad");
    }
    setPhase("checks", "done");
    setProgress(0.66);

    // ---- phase 4: real CLI
    setPhase("cli", "active");
    log(`POST /api/terminal · ${thePlan.commands.length} baris`, "cmd");
    try {
      const results = await cli(thePlan.commands);
      const last = results[results.length - 1];
      showCli(last.parsed || last.stdout, `exit ${last.exit_code}`);
      results.forEach(r => {
        log(`$ ${r.command} → exit ${r.exit_code}`, r.exit_code === 0 ? "ok" : "err");
      });
      const doctor = results[0] && results[0].parsed;
      if (doctor && doctor.skills) {
        addResult("✓", "CLI sebenar dijalankan",
          `${doctor.skills.length} skill dilaporkan oleh omniforge doctor`);
      }
      const chain = results.find(r => r.command === "ofprov snapshot" && r.parsed);
      if (chain) {
        addResult("⛓", "Rantai provenance dibina",
          `blok ${chain.parsed.seq} · ${String(chain.parsed.entry_hash || "").slice(0, 16)}…`);
      }
    } catch (error) {
      log(error.message, "err");
      addResult("✕", "CLI gagal", error.message, "bad");
    }
    setPhase("cli", "done");
    setProgress(0.86);

    // ---- phase 5: report
    setPhase("report", "active");
    await pause(260);
    addResult("✓", "Selesai",
      "Prompt → pelan → GitHub API → CLI sebenar. Tiada model bahasa digunakan.");
    setPhase("report", "done");
    setProgress(1);
    resultMeta.textContent = "selesai";
    setStatus("SELESAI", "done");
    log("selesai.", "ok");

    running = false;
    runBtn.disabled = false;
  }

  // ---------------------------------------------------------------- events

  runBtn.addEventListener("click", run);

  $("presets").addEventListener("click", event => {
    const button = event.target.closest("[data-prompt]");
    if (!button) return;
    promptInput.value = button.dataset.prompt;
    promptInput.focus();
  });

  promptInput.addEventListener("keydown", event => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      run();
    }
  });

  setStatus("SEDIA", "idle");
})();
