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

  const buttons = {
    build: document.getElementById("btnBuild"),
    append: document.getElementById("btnAppend"),
    tamper: document.getElementById("btnTamper"),
    verify: document.getElementById("btnVerify"),
    reset: document.getElementById("btnReset"),
  };

  /** Mirror of the ledger that the server last confirmed. */
  let state = {
    initialised: false,
    blocks: [],       // {seq, hash, prevHash, note}
    tampered: false,
    verified: false,
    snapshots: 0,     // how many snapshots this session has appended
  };
  let busy = false;

  // ---------------------------------------------------------------- helpers

  function setStatus(text, kind) {
    statusPill.textContent = text;
    statusPill.dataset.state = kind || "idle";
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

  /** Render JSON with light colouring so 64-char hashes stay readable. */
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
  }

  // ---------------------------------------------------------------- server

  /**
   * Run an ordered batch in ONE disposable project.
   * Returns the per-command results, each with parsed stdout where possible.
   */
  async function runBatch(commands) {
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
    syncButtons();
  }

  // ---------------------------------------------------------------- actions

  /** Build the genesis block: init + first snapshot in one project. */
  async function build() {
    setBusy(true);
    setStatus("MEMBINA…", "running");
    showText("$ ofprov init\n$ ofprov snapshot\n\nMenjalankan Python sebenar…");
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
    } catch (error) {
      fail(error.message);
    } finally {
      setBusy(false);
    }
  }

  /**
   * Append one block. The server rebuilds the whole session in one project, so
   * we replay init + every previous snapshot + one new snapshot.
   */
  async function append() {
    setBusy(true);
    setStatus("MENAMBAH…", "running");
    const count = state.snapshots + 1;
    const commands = ["ofprov init", ...Array(count).fill("ofprov snapshot")];
    if (commands.length > MAX_BATCH) {
      setBusy(false);
      fail(`Had pelayan ialah ${MAX_BATCH} baris setiap permintaan; rantai ini sudah penuh. `
           + "Tekan Set semula untuk mula rantai baru.");
      return;
    }
    showText(`$ ${commands.join("\n$ ")}\n\nMenjalankan Python sebenar…`);
    try {
      const results = await runBatch(commands);
      const failures = results.filter(r => r.exit_code !== 0);
      if (failures.length) throw new Error(stderrOf(failures[0]));

      // Rebuild block list from every snapshot result (all real hashes).
      const snaps = results.slice(1);
      const blocks = snaps.map((result, index) => ({
        seq: result.parsed?.seq ?? index,
        hash: result.parsed?.entry_hash || "",
        prevHash: index === 0 ? null : (snaps[index - 1].parsed?.entry_hash || null),
        note: index === 0 ? "genesis" : "snapshot",
      }));
      state.blocks = blocks;
      state.snapshots = snaps.length;
      state.tampered = false;
      state.verified = false;
      render();

      const newest = snaps[snaps.length - 1].parsed || {};
      showJSON({
        batch_commands: commands.length,
        newest_seq: newest.seq,
        newest_entry_hash: newest.entry_hash,
        prev_hash: snaps.length > 1 ? snaps[snaps.length - 2].parsed?.entry_hash : null,
        snapshot_hash: newest.snapshot_hash,
      }, `EXIT 0 · ${blocks.length} blok dalam rantai`);
      setStatus(`${blocks.length} BLOK`, "ok");
    } catch (error) {
      fail(error.message);
    } finally {
      setBusy(false);
    }
  }

  /** Rewrite a sample file, then verify: tamper-demo exits 1 when detected. */
  async function tamper() {
    setBusy(true);
    setStatus("MENGUBAH…", "running");
    const commands = ["ofprov init", ...Array(state.snapshots).fill("ofprov snapshot"),
                      "ofprov tamper-demo"];
    showText(`$ ofprov tamper-demo\n\n(Projek dibina semula: ${commands.length - 1} langkah, `
             + "kemudian fail sampel diubah dan disahkan.)\n\nMenjalankan Python sebenar…");
    try {
      const results = await runBatch(commands);
      const tamperResult = results[results.length - 1];
      const payload = tamperResult.parsed || {};
      const detected = tamperResult.exit_code === 1 && payload.ok === false;

      state.tampered = detected;
      state.verified = false;
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
    } catch (error) {
      fail(error.message);
    } finally {
      setBusy(false);
    }
  }

  /** Verify chain integrity plus current files. */
  async function verify() {
    setBusy(true);
    setStatus("MENGESAHKAN…", "running");
    const commands = ["ofprov init", ...Array(state.snapshots).fill("ofprov snapshot"),
                      "ofprov verify"];
    showText(`$ ofprov verify\n\n(Projek dibina semula: ${commands.length - 1} langkah.)\n\n`
             + "Menjalankan Python sebenar…");
    try {
      const results = await runBatch(commands);
      const last = results[results.length - 1];
      const payload = last.parsed || {};
      const ok = last.exit_code === 0 && payload.ok === true;
      state.verified = ok;
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
    } catch (error) {
      fail(error.message);
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    state = { initialised: false, blocks: [], tampered: false, verified: false, snapshots: 0 };
    render();
    showText("$ menunggu arahan…");
    outputMeta.textContent = "—";
    setStatus("SEDIA", "idle");
  }

  // ---------------------------------------------------------------- events

  buttons.build.addEventListener("click", build);
  buttons.append.addEventListener("click", append);
  buttons.tamper.addEventListener("click", tamper);
  buttons.verify.addEventListener("click", verify);
  buttons.reset.addEventListener("click", reset);

  document.addEventListener("keydown", event => {
    if (event.target.matches("input, textarea")) return;
    const map = { "1": build, "2": append, "3": tamper, "4": verify };
    const action = map[event.key];
    if (action && !busy) { event.preventDefault(); action(); }
  });

  render();
  setStatus("SEDIA", "idle");
})();
