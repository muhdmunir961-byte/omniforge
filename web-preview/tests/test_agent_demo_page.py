"""Static contract tests for the Agent Demo page.

These assert the page is honest about what it does: real GitHub API calls, real
CLI calls, and an explicitly deterministic planner rather than a language model.
They do not run a browser or make network requests.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "agent-demo.html").read_text(encoding="utf-8")
JS = (ROOT / "agent-demo.js").read_text(encoding="utf-8")
CSS = (ROOT / "agent-demo.css").read_text(encoding="utf-8")


def test_assets_exist_and_are_linked():
    for name in ("agent-demo.css", "agent-demo.js"):
        assert (ROOT / name).is_file(), f"missing {name}"
        assert f"/{name}" in HTML, f"{name} not referenced"


def test_every_element_the_script_uses_exists():
    ids = set(re.findall(r'\$\("([^"]+)"\)', JS))
    assert ids, "script queries no elements"
    for element_id in sorted(ids):
        assert f'id="{element_id}"' in HTML, f"script needs #{element_id}"


def test_uses_real_github_api():
    assert "https://api.github.com" in JS
    assert "/repos/" in JS
    assert "check-runs" in JS
    assert "commits?per_page" in JS


def test_uses_real_cli_endpoint_not_a_fake():
    assert '"/api/terminal"' in JS
    assert "fetch(CLI" in JS
    # The CLI commands must stay within the server's 4-line batch ceiling.
    assert "slice(0, 4)" in JS


def test_planner_is_deterministic_and_says_so():
    """No model is called; the page must not imply one is."""
    assert "function plan(" in JS
    assert "keyword" in JS.lower()
    # It must not call any model endpoint.
    for host in ("api.deepseek", "api.openai", "anthropic.com", "generativelanguage"):
        assert host not in JS.lower(), f"page calls a model provider: {host}"
    assert "model endpoint" not in JS.lower() or "must not" in JS.lower()


def test_does_not_claim_model_use_in_user_facing_ui():
    """The visible text must not claim a model runs; source comments may explain."""
    # Strip HTML comments and JS block comments before checking the surface.
    html_visible = re.sub(r"<!--.*?-->", "", HTML, flags=re.S)
    js_visible = re.sub(r"/\*.*?\*/", "", JS, flags=re.S)
    visible = (html_visible + js_visible).lower()
    for name in ("deepseek", "gpt-4", "claude-3", "gemini-pro"):
        assert name not in visible, f"UI claims to use {name}"
    # It must state plainly that no language model is used.
    assert "tiada model bahasa" in visible or "no language model" in visible


def test_reports_unauthenticated_rate_limit():
    """A public API has a 60/hour cap; the UI should surface it."""
    assert "ratelimit-remaining" in JS
    assert "kuota" in JS.lower() or "quota" in JS.lower()


def test_all_phases_have_a_visual_step():
    for phase in ("plan", "repo", "checks", "cli", "report"):
        assert f'id: "{phase}"' in JS, f"missing phase {phase}"
    assert 'id="phaseList"' in HTML
    assert 'id="progressBar"' in HTML


def test_keyboard_shortcut_runs():
    assert "metaKey" in JS or "ctrlKey" in JS
    assert "Enter" in JS


def test_reduced_motion_is_respected():
    assert "prefers-reduced-motion" in CSS
    reduced = CSS.split("prefers-reduced-motion")[-1]
    assert "animation: none" in reduced


def test_assets_are_local_only():
    """Only the GitHub API may be remote; everything else is same-origin."""
    stripped = HTML.replace("http://www.w3.org/2000/svg", "")
    assert "https://" not in stripped.replace("https://github.com/muhdmunir961-byte/omniforge", "")
    for match in re.findall(r'(?:src|href)="(https?://[^"]+)"', HTML):
        assert "github.com" in match, f"unexpected remote asset {match}"
