"""#248 U7–U12 — Comet-style agent busy UX (static contract).

Edge/vignette glow only; no full-field wash; no center bar.
U8: visible corner chip ≤220×36 (not sr-only, not centered strip).
"""

from __future__ import annotations

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "lca_wrench" / "static"


def _agent_hold_css_block(css: str) -> str:
    m = re.search(r"/\* Planet A #248.*?agent busy.*?\*/(.*)", css, re.S | re.I)
    assert m, "missing #248 agent busy CSS section"
    return m.group(1)


def _hue_rule(block: str) -> str:
    m = re.search(r"\.agent-hold-hue\{([^}]*)\}", block)
    assert m, "missing .agent-hold-hue rule"
    return m.group(1)


def _status_rule(block: str) -> str:
    m = re.search(r"\.agent-hold-status\{([^}]*)\}", block)
    assert m, "missing .agent-hold-status rule"
    return m.group(1)


def test_hold_markup_is_edge_glow_not_modal():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert 'id="agentHold"' in html
    hold = html.split('id="agentHold"', 1)[1].split('<div class="toast"', 1)[0]
    assert "aria-modal" not in hold
    assert "agent-hold-hue" in hold
    assert "agent-hold-status" in hold or "agentHoldTitle" in hold
    assert "Agent working" in hold or "Agent arbeitet" in hold
    # U8: no center strip / card
    assert "agent-hold-strip" not in hold
    assert "agent-hold-card" not in hold


def test_hold_css_edge_only_no_center_bar():
    """U7 + U12: edge vignette only; U8: no centered strip."""
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    block = _agent_hold_css_block(css)
    hue = _hue_rule(block)

    assert "pointer-events:auto" in block.replace(" ", "") or "pointer-events: auto" in block
    assert "backdrop-filter" not in block
    assert "place-items:center" not in block.replace(" ", "")

    # U7/U12: hue fill must be transparent — no full-field accent/fg wash
    assert re.search(r"background\s*:\s*transparent", hue), "hue must use transparent background"
    assert "box-shadow" in hue and "inset" in hue, "edge glow requires inset box-shadow"
    # Forbid wash-style color-mix fill on .agent-hold-hue background
    assert not re.search(r"background\s*:\s*color-mix", hue), "no full-field color-mix wash on hue"

    # U8/U12: no center bar positioning
    assert "left:50%" not in block.replace(" ", "")
    assert "translateX(-50%)" not in block.replace(" ", "")
    assert ".agent-hold-strip" not in block


def test_hold_status_is_visible_corner_chip():
    """U8: chip visible when busy — corner ≤220×36; not sr-only; not center."""
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    block = _agent_hold_css_block(css)
    status = _status_rule(block)
    compact = status.replace(" ", "")

    # Visible chip — not sr-only clip/1px hide
    assert "clip:rect" not in compact
    assert "clip-path" not in compact
    assert "width:1px" not in compact
    assert "height:1px" not in compact
    assert "sr-only" not in block

    # Corner placement (bottom-right or top-right), not center
    assert "right:" in compact
    assert "bottom:" in compact or "top:" in compact
    assert "left:50%" not in compact
    assert "translateX(-50%)" not in compact

    # Size ceiling ≤220×36
    assert re.search(r"max-width\s*:\s*220px", status)
    assert re.search(r"max-height\s*:\s*36px", status)


def test_sync_agent_hold_still_toggles_hidden():
    js = (STATIC / "js" / "main.js").read_text(encoding="utf-8")
    assert "function syncAgentHold(busy)" in js
    assert "el.hidden = !on" in js
    assert "agentHoldTitle" in js
