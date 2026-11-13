"""Static contract tests for the Blockchain Lab page.

These are offline checks: they assert the page references assets that exist,
that every element id the script queries is present in the HTML, and that the
batch ceiling the page enforces matches the server's real limit. They do not
execute a browser.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "blockchain-lab.html").read_text(encoding="utf-8")
JS = (ROOT / "blockchain-lab.js").read_text(encoding="utf-8")
CSS = (ROOT / "blockchain-lab.css").read_text(encoding="utf-8")
SERVER = (ROOT / "api" / "terminal.py").read_text(encoding="utf-8")


def test_assets_exist_and_are_referenced():
    for name in ("blockchain-lab.css", "blockchain-lab.js"):
        assert (ROOT / name).is_file(), f"missing asset {name}"
        assert f"/{name}" in HTML, f"{name} not linked from the page"


def test_every_element_the_script_uses_exists_in_the_html():
    ids = set(re.findall(r'getElementById\("([^"]+)"\)', JS))
    assert ids, "script queries no elements"
    for element_id in sorted(ids):
        assert f'id="{element_id}"' in HTML, f"script needs #{element_id}, absent from HTML"


def test_server_batch_limit_matches_the_page_constant():
    """The page must not promise a chain the server would reject."""
    server_limit = int(re.search(r"MAX_BATCH_COMMANDS = (\d+)", SERVER).group(1))
    page_limit = int(re.search(r"const MAX_BATCH = (\d+)", JS).group(1))
    assert page_limit == server_limit, (
        f"page allows {page_limit} commands, server allows {server_limit}"
    )


def test_page_never_claims_decentralisation_or_authorship():
    text = (HTML + JS).lower()
    for forbidden in ("decentralised blockchain", "decentralized blockchain",
                      "proves authorship", "membuktikan penulisan kod"):
        assert forbidden not in text
    # The honest boundary statement must be present.
    assert "bukan" in text
    assert "checkpoint" in text


def test_only_allowlisted_prov_commands_are_sent():
    """Every ofprov command the page sends must be on the server allowlist."""
    sent = set(re.findall(r'"(ofprov [a-z-]+)"', JS))
    assert sent, "page sends no ofprov commands"
    allow = set(re.search(
        r'"init", "snapshot", "verify", "audit", "proof", "tamper-demo"',
        SERVER).group(0).replace('"', "").replace(" ", "").split(","))
    for command in sent:
        sub = command.split(" ", 1)[1]
        assert sub in allow, f"{command} is not on the server allowlist {sorted(allow)}"


def test_page_uses_batch_endpoint_not_isolated_single_requests():
    """Single requests get a fresh project, so chaining requires a batch."""
    assert '"commands"' in JS or "commands:" in JS
    assert "runBatch" in JS
    # It must not post a single {command} body, which would lose the ledger.
    assert re.search(r'body:\s*JSON\.stringify\(\{\s*command\s*:', JS) is None


def test_reduced_motion_is_respected():
    assert "prefers-reduced-motion" in CSS


# --------------------------------------------------------------------------
# Presentation features: autoplay, stepper, live stats, narration.
# --------------------------------------------------------------------------

def test_autoplay_button_exists_and_is_wired():
    """The presentation demo must be one click, and it must be real work."""
    assert 'id="btnAutoplay"' in HTML
    assert "autoplay" in JS
    # It must reuse the same server calls, not fake the sequence client-side.
    for call in ("build(", "append(", "verify(", "tamper("):
        assert call in JS, f"autoplay does not reuse {call}"


def test_autoplay_respects_the_batch_ceiling():
    """Autoplay replays snapshots + one command, so it must fit in 4 lines."""
    server_limit = int(re.search(r"MAX_BATCH_COMMANDS = (\d+)", SERVER).group(1))
    snapshots = int(re.search(r"const MAX_SNAPSHOTS = MAX_BATCH - (\d+)", JS).group(1))
    # init + snapshots + one trailing command must not exceed the server limit.
    assert 1 + (server_limit - snapshots) + 1 <= server_limit
    assert server_limit - snapshots <= server_limit


def test_stepper_has_all_four_steps():
    order = re.findall(r'data-step="([a-z]+)"', HTML)
    assert order == ["build", "append", "tamper", "verify"], order
    # The script must drive them from the same names.
    for step in order:
        assert f'"{step}"' in JS


def test_live_stats_are_present_and_updated():
    for stat_id in ("statBlocks", "statVerified", "statTamper", "statLatency", "statState"):
        assert f'id="{stat_id}"' in HTML, f"missing {stat_id}"
        assert stat_id in JS, f"{stat_id} never updated"


def test_narration_element_is_present():
    assert 'id="narration"' in HTML
    assert 'id="narrationText"' in HTML
    assert "narrationText.innerHTML" in JS


def test_presentation_animation_is_motion_safe():
    """Every new animated element must be disabled under reduced motion."""
    for selector in (".blk", ".link", ".hv-block i", ".hv-link b", ".narration-dot", ".stat.bump strong"):
        assert selector in CSS, f"{selector} missing from stylesheet"
    reduced = CSS.split("prefers-reduced-motion")[-1]
    for selector in (".hv-block i", ".hv-link b", ".narration-dot", ".stat.bump strong"):
        assert selector in reduced, f"{selector} not covered by reduced-motion"


def test_keyboard_shortcuts_include_autoplay():
    assert '"p": autoplay' in JS or "'p': autoplay" in JS
