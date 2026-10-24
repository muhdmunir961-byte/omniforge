# OmniForge System Explorer — Vercel preview

This is a **static interactive explainer** for the open-source OmniForge Python CLI v1.3.1, not a hosted OmniForge runtime.

**Live preview:** https://omniforge-explorer.vercel.app

It covers nine pages: overview, all 14 packaged skills, a clearly labeled **browser-only simulated CLI**, MCP tool schemas (10), editable workflow DAG validation, a **real browser Web Crypto SHA-256** v2-style hash-chain demonstration, runtime permission planning, architecture/source links, and read-only public GitHub Actions evidence.

## Scope and privacy

- Pure HTML/CSS/ES modules; no npm dependencies, wallet handling or backend APIs.
- Client-side demonstration state lives in memory; refreshing clears toy files and ledger.
- CLI responses are **educational simulations**, not the actual Python CLI; no commands or Docker tasks execute remotely.
- MCP interactions generate JSON-RPC envelopes, not connections to a local stdio process.
- Workflow studio validates example DAGs in the browser; the real OmniForge CLI is authoritative for execution approval and validation.
- The provenance lab computes SHA-256 using browser `crypto.subtle` but uses an illustrative scan policy. It does not attest the GitHub repository, recover files, store wallet keys or broadcast transactions.
- Optional live GitHub status fetch makes browser requests only to the public GitHub REST API on explicit user click; rate limits may apply.
- This explorer does not run AI models, upload selected files or access serial ports/hardware.
- The preview is hosted as a **separate Vercel project** rather than modifying the existing Python CLI deployment behavior.

## Local static preview

Run `python -m http.server 8765 --directory web-preview` in the repo root and open `http://localhost:8765`. For a real CLI, use the repo root and `python -m pip install -e .`.

## Source and features

- `index.html` – shell/navigation plus all page layouts.
- `style.css` – responsive classic light presentation.
- `data.js` – accurate packaged-skill/MCP/architecture metadata from source inspection.
- `app.js` – client-side controls, sample data and browser hashing.

This is intentionally not an authentication gateway or remote command runner. Do not send secrets to a public demo.
