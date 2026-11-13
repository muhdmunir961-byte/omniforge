/* Blockchain Lab.
 *
 * Every button posts to /api/terminal, which runs the real OmniForge CLI.
 * A single request = a single disposable project, so actions that must share a
 * ledger are sent as ONE batch. That is the server's real contract: separate
 * requests cannot continue the same chain, and this page never pretends
 * otherwise.
 */
(function () {
  "use strict";

  const API = "/api/terminal";
  /**
   * Server-enforced ceiling: one batch = one disposable project, max 4 lines.
   * tamper/verify replay the snapshots and then append one line, so the chain
   * itself may hold at most 2 snapshots (init + 2 = 3, plus 1 = 4).
   */
  const MAX_BATCH = 4;
  const MAX_SNAPSHOTS = MAX_BATCH - 2;

  const rail = document.getElementById("rail");
  const stage = document.getElementById("stage");
  const stageEmpty = document.getElementById("stageEmpty");
  const output = document.getElementById("output");
  const outputMeta = document.getElementById("outputMeta");
  const statusPill = document.getElementById("statusPill");
  const narration = document.getElementById("narration");
  const narrationText = document.getElementById("narrationText");
  const stepper = document.getElementById("stepper");

  const buttons = {
    build: document.getElementById("btnBuild"),
    append: document.getElementById("btnAppend"),
    tamper: document.getElementById("btnTamper"),
    verify: document.getElementById("btnVerify"),
    reset: document.getElementById("btnReset"),
    autoplay: document.getElementById("btnAutoplay"),
  };

  const stats = {
    blocks: document.getElementById("statBlocks"),
    verified: document.getElementById("statVerified"),
    tamper: document.getElementById("statTamper"),
    latency: document.getElementById("statLatency"),
    state: document.getElementById("statState"),
  };

  /** Mirror of the ledger that the server last confirmed. */
  let state = {
    initialised: false,
    blocks: [],       // {seq, hash, prevHash, note}
    tampered: false,
    verified: false,
    snapshots: 0,
  };
  let counters = { blocks: 0, verified: 0, tamper: 0 };
  let busy = false;
  let autoplayRunning = false;

  // ---------------------------------------------------------------- helpers

  function setStatus(text, kind) {
    statusPill.textContent = text;
    statusPill.dataset.state = kind || "idle";
    stats.state.textContent = text;
    stats.state.parentElement.className = "stat stat-wide";
    if (kind === "ok") stats.state.parentElement.classList.add("good");
    if (kind === "bad") stats.state.parentElement.classList.add("tampered");
  }

  function bumpStat(node) {
    const card = node.closest(".stat");
    card.classList.remove("bump");
    // force reflow so the animation can restart
    void card.offsetWidth;
    card.classList.add("bump");
    setTimeout(() => card.classList.remove("bump"), 450);
  }

  function renderCounters() {
    stats.blocks.textContent = counters.blocks;
    stats.verified.textContent = counters.verified;
    stats.tamper.textContent = counters.tamper;
  }

  function setStep(name) {
    const order = ["build", "append", "tamper", "verify"];
    const activeIndex = order.indexOf(name);
    stepper.querySelectorAll(".step").forEach(step => {
      const idx = order.indexOf(step.dataset.step);
      step.classList.toggle("active", idx === activeIndex);
      step.classList.toggle("done", activeIndex > -1 && idx < activeIndex);
    });
  }

  function say(text) {
    narrationText.innerHTML = text;
    narration.hidden = false;
    narration.style.animation = "none";
    void narration.offsetWidth;
    narration.style.animation = "";
  }

  function setBusy(value) {
    busy = value;
    Object.values(buttons).forEach(b => { b.disabled = value; });
    if (!value) syncButtons();
  }

  function syncButtons() {
    buttons.build.disabled = busy || state.blocks.length > 0;
    buttons.append.disabled = busy || !state.initialised || state.snapshots >= MAX_SNAPSHOTS;
    buttons.tamper.disabled = busy || !state.initialised;
    buttons.verify.disabled = busy || !state.initialised;
    buttons.reset.disabled = busy;
    buttons.autoplay.disabled = busy;
    buttons.append.title = state.snapshots >= MAX_SNAPSHOTS
      ? `Had pelayan: ${MAX_BATCH} baris setiap permintaan (init + ${MAX_SNAPSHOTS} snapshot)`
      : "";
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function shortHash(h) {
    return h ? h.slice(0, 10) + "…" + h.slice(-6) : "—";
  }

  function showJSON(obj, meta) {
    const pretty = JSON.stringify(obj, null, 2);
    const escaped = escapeHtml(pretty);
    const coloured = escaped
      .replace(/"([^"]+)":/g, '<span class="k">"$1"</span>:')
      .replace(/: "([0-9a-f]{64})"/g, ': <span class="str">"$1"</span>')
      .replace(/"ok": (true|false)/g, (m, v) =>
        `"ok": <span class="${v === "true" ? "ok" : "bad"}">${v}</span>`);
    output.innerHTML = coloured;
    if (meta) outputMeta.textContent = meta;
  }

  function showText(text) {
    output.innerHTML = "";
    output.textContent = text;
  }

  function fail(message) {
    output.innerHTML = "";
    const line = document.createElement("span");
    line.className = "bad";
    line.textContent = "RALAT: " + message;
    output.appendChild(line);
    outputMeta.textContent = "GAGAL";
    setStatus("RALAT", "bad");
    say(`Ralat: ${escapeHtml(message)}`);
  }

  // ---------------------------------------------------------------- server

  async function runBatch(commands) {
    const started = performance.now();
    const response = await fetch(API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ commands }),
      cache: "no-store",
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Pelayan menolak arahan ini.");
    }
    const elapsed = Math.round(performance.now() - started);
    stats.latency.textContent = elapsed + " ms";
    bumpStat(stats.latency);
    return (data.results || []).map(result => {
      let parsed = null;
      try { parsed = JSON.parse(result.stdout); } catch (_) { /* raw only */ }
      return { ...result, parsed: parsed && typeof parsed === "object" ? parsed : null };
    });
  }

  function stderrOf(result) {
    return (result && (result.stderr || result.error)) || "Arahan gagal.";
  }

  // ---------------------------------------------------------------- render

  function render() {
    rail.innerHTML = "";
    const hasBlocks = state.blocks.length > 0;
    rail.classList.toggle("is-empty", !hasBlocks);
    stageEmpty.style.display = hasBlocks ? "none" : "grid";

    state.blocks.forEach((block, index) => {
      const isLast = index === state.blocks.length - 1;
      const broken = state.tampered && isLast;

      if (index > 0) {
        const link = document.createElement("div");
        link.className = "link" + (broken ? " bad" : "");
        link.style.animationDelay = (index * 80) + "ms";
        rail.appendChild(link);
      }

      const el = document.createElement("article");
      el.className = "blk" + (broken ? " bad" : (state.verified ? " verified" : ""));
      el.style.animationDelay = (index * 100) + "ms";
      el.innerHTML = `
        <div class="blk-head">
          <span class="blk-idx">BLOCK ${block.seq}</span>
          <span class="blk-note">${escapeHtml(block.note)}</span>
        </div>
        <span class="blk-label">ENTRY HASH · SHA-256</span>
        <div class="blk-hash" title="${escapeHtml(block.hash || "")}">${escapeHtml(shortHash(block.hash))}</div>
        <span class="blk-label">PREV HASH</span>
        <div class="blk-hash">${escapeHtml(block.prevHash ? shortHash(block.prevHash) : "genesis")}</div>
        <div class="blk-foot">
          <span class="blk-dot"></span>
          <span>${broken ? "fail diubah selepas snapshot" : "direkod"}</span>
        </div>`;
      rail.appendChild(el);
    });

    const links = rail.querySelectorAll(".link");
    if (links.length) {
      const last = links[links.length - 1];
      last.classList.add("flow");
      setTimeout(() => last.classList.remove("flow"), 2400);
    }
    renderCounters();
    syncButtons();
  }

  // ---------------------------------------------------------------- actions

  async function build(options = {}) {
    if (!options.silent) setStep("build");
    setBusy(true);
    setStatus("MEMBINA…", "running");
    showText("$ ofprov init\n$ ofprov snapshot\n\nMenjalankan Python sebenar…");
    say("<strong>Langkah 1.</strong> Mencipta ledger baru dan snapshot pertama — blok genesis.");
    try {
      const results = await runBatch(["ofprov init", "ofprov snapshot"]);
      const init = results[0];
      const snap = results[1];
      if (init.exit_code !== 0) throw new Error(stderrOf(init));
      if (snap.exit_code !== 0) throw new Error(stderrOf(snap));

      const block = snap.parsed || {};
      state = {
        initialised: true,
        blocks: [{ seq: block.seq ?? 0, hash: block.entry_hash || "", prevHash: null, note: "genesis" }],
        tampered: false,
        verified: false,
        snapshots: 1,
      };
      counters.blocks += 1;
      bumpStat(stats.blocks);
      render();
      showJSON({
        batch: ["ofprov init", "ofprov snapshot"],
        seq: block.seq,
        entry_hash: block.entry_hash,
        snapshot_hash: block.snapshot_hash,
        policy_hash: block.policy_hash,
        files: block.files,
      }, "EXIT 0 · genesis direkod");
      setStatus("GENESIS SIAP", "ok");
      say(`<strong>Genesis direkod.</strong> Hash <code>${escapeHtml((block.entry_hash || "").slice(0, 16))}…</code> ialah cap jari SHA-256 bagi ${block.files ?? "?"} fail. Belum ada blok sebelumnya.`);
      return true;
    } catch (error) {
      fail(error.message);
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function append(options = {}) {
    if (!options.silent) setStep("append");
    setBusy(true);
    setStatus("MENAMBAH…", "running");
    const count = state.snapshots + 1;
    const commands = ["ofprov init", ...Array(count).fill("ofprov snapshot")];
    if (commands.length > MAX_BATCH) {
      setBusy(false);
      fail(`Had pelayan ialah ${MAX_BATCH} baris setiap permintaan; rantai ini sudah penuh. `
           + "Tekan Set semula untuk mula rantai baru.");
      return false;
    }
    showText(`$ ${commands.join("\n$ ")}\n\nMenjalankan Python sebenar…`);
    say("<strong>Langkah 2.</strong> Menambah blok baru yang mengunci hash blok sebelumnya.");
    try {
      const results = await runBatch(commands);
      const failures = results.filter(r => r.exit_code !== 0);
      if (failures.length) throw new Error(stderrOf(failures[0]));

      const snaps = results.slice(1);
      state.blocks = snaps.map((result, index) => ({
        seq: result.parsed?.seq ?? index,
        hash: result.parsed?.entry_hash || "",
        prevHash: index === 0 ? null : (snaps[index - 1].parsed?.entry_hash || null),
        note: index === 0 ? "genesis" : "snapshot",
      }));
      state.snapshots = snaps.length;
      state.tampered = false;
      state.verified = false;
      counters.blocks += 1;
      bumpStat(stats.blocks);
      render();

      const newest = snaps[snaps.length - 1].parsed || {};
      const prev = snaps.length > 1 ? snaps[snaps.length - 2].parsed?.entry_hash : null;
      showJSON({
        batch_commands: commands.length,
        newest_seq: newest.seq,
        newest_entry_hash: newest.entry_hash,
        prev_hash: prev,
        snapshot_hash: newest.snapshot_hash,
      }, `EXIT 0 · ${state.blocks.length} blok dalam rantai`);
      setStatus(`${state.blocks.length} BLOK`, "ok");
      say(`<strong>Blok ${newest.seq} ditambah.</strong> Ia menyimpan <code>prev_hash</code> blok sebelumnya, jadi kedua-duanya kini terikat.`);
      return true;
    } catch (error) {
      fail(error.message);
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function tamper(options = {}) {
    if (!options.silent) setStep("tamper");
    setBusy(true);
    setStatus("MENGUBAH…", "running");
    const commands = ["ofprov init", ...Array(state.snapshots).fill("ofprov snapshot"),
                      "ofprov tamper-demo"];
    showText(`$ ofprov tamper-demo\n\n(Projek dibina semula: ${commands.length - 1} langkah, `
             + "kemudian fail sampel diubah dan disahkan.)\n\nMenjalankan Python sebenar…");
    say("<strong>Langkah 3.</strong> Menukar satu fail selepas snapshot, kemudian mengesahkan.");
    try {
      const results = await runBatch(commands);
      const tamperResult = results[results.length - 1];
      const payload = tamperResult.parsed || {};
      const detected = tamperResult.exit_code === 1 && payload.ok === false;

      state.tampered = detected;
      state.verified = false;
      if (detected) {
        counters.tamper += 1;
        bumpStat(stats.tamper);
      }
      render();
      if (detected) {
        stage.classList.add("shake");
        setTimeout(() => stage.classList.remove("shake"), 500);
      }
      showJSON({
        command: "ofprov tamper-demo",
        exit_code: tamperResult.exit_code,
        ok: payload.ok,
        reason: payload.reason,
        files: payload.files,
        expected: "exit 1 + ok:false when a file changed after the snapshot",
      }, detected ? "EXIT 1 · manipulasi dikesan" : "TIDAK DIJANGKA");
      setStatus(detected ? "MANIPULASI DIKESAN" : "TIADA PERUBAHAN",
                detected ? "bad" : "ok");
      say(detected
        ? `<strong>Manipulasi dikesan.</strong> <code>verify --check-files</code> melaporkan fail berubah: <code>${escapeHtml((payload.files?.modified || []).join(", ") || "—")}</code>. Rantai tidak lagi sepadan dengan fail.`
        : "<strong>Tiada perubahan dikesan.</strong> Fail sampel mungkin tidak berubah.");
      return detected;
    } catch (error) {
      fail(error.message);
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function verify(options = {}) {
    if (!options.silent) setStep("verify");
    setBusy(true);
    setStatus("MENGESAHKAN…", "running");
    const commands = ["ofprov init", ...Array(state.snapshots).fill("ofprov snapshot"),
                      "ofprov verify"];
    showText(`$ ofprov verify\n\n(Projek dibina semula: ${commands.length - 1} langkah.)\n\n`
             + "Menjalankan Python sebenar…");
    say("<strong>Langkah 4.</strong> Menyemak setiap pautan hash dalam rantai.");
    try {
      const results = await runBatch(commands);
      const last = results[results.length - 1];
      const payload = last.parsed || {};
      const ok = last.exit_code === 0 && payload.ok === true;
      state.verified = ok;
      if (ok) {
        counters.verified += 1;
        bumpStat(stats.verified);
      }
      render();
      showJSON({
        command: "ofprov verify",
        exit_code: last.exit_code,
        ok: payload.ok,
        entries: payload.entries,
        head: payload.head,
        trusted_checkpoint: payload.trusted_checkpoint,
        anchor_evidence_events: payload.anchor_evidence_events,
      }, ok ? "EXIT 0 · rantai utuh" : "EXIT 1 · rantai tidak sepadan");
      setStatus(ok ? "RANTAI UTUH" : "RANTAI TERPUTUS", ok ? "ok" : "bad");
      say(ok
        ? `<strong>Rantai utuh.</strong> ${payload.entries} entri disahkan; kepala rantai <code>${escapeHtml((payload.head || "").slice(0, 16))}…</code>.`
        : "<strong>Rantai tidak sepadan.</strong> Satu atau lebih pautan hash gagal disahkan.");
      return ok;
    } catch (error) {
      fail(error.message);
      return false;
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    state = { initialised: false, blocks: [], tampered: false, verified: false, snapshots: 0 };
    counters = { blocks: 0, verified: 0, tamper: 0 };
    render();
    showText("$ menunggu arahan…");
    outputMeta.textContent = "—";
    stats.latency.textContent = "—";
    setStatus("SEDIA", "idle");
    narration.hidden = true;
    setStep(null);
  }

  // ---------------------------------------------------------------- autoplay

  async function autoplay() {
    if (autoplayRunning || busy) return;
    autoplayRunning = true;
    buttons.autoplay.disabled = true;
    try {
      reset();
      await pause(260);
      if (!(await build({ silent: true }))) return;
      await pause(950);
      if (!(await append({ silent: true }))) return;
      await pause(950);
      await verify({ silent: true });
      await pause(1100);
      await tamper({ silent: true });
      await pause(1100);
      await verify({ silent: true });
      say("<strong>Demo selesai.</strong> Empat langkah, semua dijalankan oleh Python sebenar. Cuba sendiri dengan butang di atas.");
    } finally {
      autoplayRunning = false;
      buttons.autoplay.disabled = false;
      syncButtons();
    }
  }

  function pause(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // ---------------------------------------------------------------- events

  buttons.build.addEventListener("click", () => build());
  buttons.append.addEventListener("click", () => append());
  buttons.tamper.addEventListener("click", () => tamper());
  buttons.verify.addEventListener("click", () => verify());
  buttons.reset.addEventListener("click", reset);
  buttons.autoplay.addEventListener("click", autoplay);

  document.addEventListener("keydown", event => {
    if (event.target.matches("input, textarea")) return;
    const map = {
      "1": () => build(),
      "2": () => append(),
      "3": () => tamper(),
      "4": () => verify(),
      "p": autoplay,
      "P": autoplay,
    };
    const action = map[event.key];
    if (action && !busy) { event.preventDefault(); action(); }
  });

  render();
  setStatus("SEDIA", "idle");
})();
