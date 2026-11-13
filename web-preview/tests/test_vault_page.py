"""Static contract tests for the Vault (Obsidian-style graph) page.

Offline checks only: they assert the graph is built from real data, that every
element the script queries exists, and that accessibility/motion rules hold.
They do not run a browser or a canvas.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "vault.html").read_text(encoding="utf-8")
JS = (ROOT / "vault.js").read_text(encoding="utf-8")
CSS = (ROOT / "vault.css").read_text(encoding="utf-8")
DATA = (ROOT / "data.js").read_text(encoding="utf-8")


def test_assets_exist_and_are_linked():
    for name in ("vault.css", "vault.js"):
        assert (ROOT / name).is_file(), f"missing {name}"
        assert f"/{name}" in HTML, f"{name} not referenced"


def test_every_element_the_script_uses_exists():
    ids = set(re.findall(r'getElementById\("([^"]+)"\)', JS))
    assert ids, "script queries no elements"
    for element_id in sorted(ids):
        assert f'id="{element_id}"' in HTML, f"script needs #{element_id}, absent from HTML"


def test_graph_is_built_from_data_not_hardcoded():
    """The vault must read the real exports, so it tracks data.js changes."""
    assert 'from "./data.js"' in JS
    for symbol in ("SKILLS", "MCP_TOOLS", "META"):
        assert symbol in JS, f"{symbol} not imported"
    # Node ids must be derived by iterating the data, not written out.
    assert "for (const skill of SKILLS)" in JS
    assert "for (const tool of MCP_TOOLS)" in JS
    assert "new Set(SKILLS.map(s => s.category))" in JS
    # The only named mapping allowed is the readable tool->skill heuristic,
    # which is documented as a heuristic, not a formal dependency graph.
    assert "toolToSkills" in JS
    assert "heuristic" in JS.lower()


def test_canvas_is_accessible_and_labelled():
    assert 'id="graphCanvas"' in HTML
    assert "aria-label" in HTML


def test_note_panel_has_all_sections():
    for section in ("noteBadges", "noteTitle", "noteDesc", "noteMeta",
                    "noteLinks", "noteCmd", "noteClose"):
        assert f'id="{section}"' in HTML, f"missing note section {section}"


def test_list_mode_is_present():
    assert 'data-mode="list"' in HTML
    assert 'id="listView"' in HTML
    assert "renderList" in JS


def test_search_shortcut_and_escape_are_wired():
    assert 'event.key === "/"' in JS or "event.key === '/'" in JS
    assert '"Escape"' in JS or "'Escape'" in JS
    assert 'id="vaultSearch"' in HTML


def test_physics_has_a_settle_stop_and_manual_control():
    """An always-on simulation would drain battery; it must settle."""
    assert "setTimeout" in JS and "physicsOn = false" in JS
    assert 'id="btnPause"' in HTML
    assert 'id="btnReheat"' in HTML


def test_reduced_motion_is_respected():
    assert "prefers-reduced-motion" in CSS
    reduced = CSS.split("prefers-reduced-motion")[-1]
    assert "animation: none" in reduced


def test_no_remote_assets_are_loaded():
    """The vault must work offline and not leak requests to third parties."""
    # The SVG data-URI icon legitimately contains the xmlns namespace.
    stripped = HTML.replace("http://www.w3.org/2000/svg", "")
    assert "http://" not in stripped, "remote http asset referenced"
    assert "https://" not in stripped, "remote https asset referenced"
    assert "fetch(" not in JS, "vault must not fetch remote data"
    # No external stylesheet/script hosts.
    assert not re.search(r'<(?:script|link)[^>]+(?:src|href)="//', HTML)


def test_responsive_breakpoints_exist():
    assert "@media (max-width: 900px)" in CSS
    assert "@media (max-width: 620px)" in CSS
