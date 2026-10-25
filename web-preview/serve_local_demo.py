"""Develop OmniForge's showcase and *real restricted* Python API locally.

Start from repository root:
    python -m pip install -e .
    python web-preview/serve_local_demo.py
Then open http://127.0.0.1:8765/terminal.html
Binds loopback ONLY; not an internet-facing shell.
"""
from __future__ import annotations

import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from api.terminal import handler as DemoAPI


ROOT = Path(__file__).resolve().parent


class DemoSite(SimpleHTTPRequestHandler):
    _json = DemoAPI._json

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if urlsplit(self.path).path == "/api/terminal":
            return DemoAPI.do_GET(self)
        return super().do_GET()

    def do_POST(self):
        if urlsplit(self.path).path == "/api/terminal":
            return DemoAPI.do_POST(self)
        return self.send_error(404, "Only /api/terminal accepts POST")


if __name__ == "__main__":
    port = int(os.getenv("OMNIFORGE_DEMO_PORT", "8765"))
    server = ThreadingHTTPServer(("127.0.0.1", port), DemoSite)
    print(f"OmniForge product showcase: http://127.0.0.1:{port}/")
    print(f"Live Python CLI terminal: http://127.0.0.1:{port}/terminal.html")
    print("Developer server: loopback only. Press Ctrl+C to stop.")
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
