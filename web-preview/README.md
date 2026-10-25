# OmniForge: Product Showcase & Live Python Terminal

**Production:** https://omniforge-explorer.vercel.app

Three experiences are provided:

1. PRODUCT SHOWCASE (index.html): nine guided before/after cases with archived
   v1.3.0 CLI traces and separately identified E2E test fixtures.
2. TECHNICAL EXPLORER (explorer.html): 14 skills, 10 MCP tools, the simulated
   workflow DAG and browser SHA-256 educational controls.
3. EXECUTABLE PYTHON TERMINAL (terminal.html): real OmniForge CLI processes
   executed in an allowlisted Vercel Python function, plus arbitrary Python
   executed client-side in a dedicated Pyodide WebAssembly Worker.

## Genuine hosted Python CLI

The api/terminal.py route accepts a STRICT command allowlist. It imports the
installed, pinned OmniForge v1.3.1 library and executes real Python subprocesses
for these example commands:

    python --version
    omniforge doctor
    omniforge list
    omniforge search "API errors"
    omniforge related "python error"
    omniforge plan "debug python errors"
    omniforge budget --selected log-triage
    omniforge load python-symbols
    omniforge inspect
    omniforge catalog python
    ofprov init
    ofprov snapshot
    ofprov verify
    ofprov audit
    ofprov proof
    ofprov tamper-demo

Each request creates its own disposable sample Python project. For
ofprov tamper-demo the backend runs init, snapshot, modifies a safe sample file,
then verifies the changed files. A nonzero verification exit code is expected.
No history or filesystem state is shared across requests.

The public endpoint REJECTS arbitrary python -c, shell input, caller-selected
filesystem paths, arbitrary binaries, Docker, external browser actions, AI model
providers, network calls and wallet interactions. It gives subprocesses a
minimal environment excluding project secrets and credentials, limits command
length to 240 characters, JSON payloads to 1KB, subprocess time to 5 seconds
per step and displayed output to 16KB.

The API is not a general Python sandbox, and isolated temp folders are not an
OS container security boundary. Configure Vercel firewall/rate limits for
high-traffic deployments; these local guards are not a distributed rate limit.

## Browser Python Playground

The second tab uses a pinned CDN copy of Pyodide v0.27.7, based on real
CPython 3.12.7 compiled to WebAssembly. The browser downloads the engine only
when Run is clicked, then executes code inside a Worker and returns genuine
stdout/stderr/traceback. A worker watchdog stops execution after ten seconds;
Stop / reset terminates the worker, erasing its in-memory Python state.

The user must have network access to jsDelivr on the first run. This runtime
cannot access the website's server-side OmniForge installation or user device
files. Do not paste private keys or execute code from untrusted sources.
WebAssembly in a browser is not a replacement for a hardened Docker sandbox.

## Local development

From the repository root:

    python -m pip install -e . pytest playwright
    python web-preview/serve_local_demo.py

Open http://127.0.0.1:8765/terminal.html . The development site binds loopback
only and serves static pages plus the restricted real CLI API.

Static-only mode (API unavailable):

    python -m http.server 8765 --directory web-preview

## Source code & test verification

- Homepage: index.html, showcase.css, refinement.css, showcase.js
- Technical explorer: explorer.html, style.css, data.js, app.js
- Terminal UI: terminal.html, terminal.css, terminal.js
- Python WebAssembly: py-worker.js
- Vercel Python function: api/terminal.py
- Dependency pinning: requirements.txt, vercel.json
- Local example server: serve_local_demo.py
- Tests: tests/test_live_terminal.py, tests/test_showcase_browser.py
- Automation: .github/workflows/showcase-ui.yml

GitHub Actions tests execute the real CLI commands, ensure dangerous inputs are
rejected, verify SHA-256 provenance tampering, exercise desktop/mobile Chromium
flows, and attempt to run actual browser Python through the pinned CDN.

Original preview traces (v1.3.0):
https://github.com/muhdmunir961-byte/omniforge/actions/runs/40131838901

Repo:
https://github.com/muhdmunir961-byte/omniforge

These are educational public demos, not permission to run the user's actual
project, sign transactions, read serial devices or autonomously modify files.
Production OmniForge workflows stay on the user's computer with local approval.
