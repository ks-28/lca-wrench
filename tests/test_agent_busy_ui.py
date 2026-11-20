"""#248 U7/U8 — Comet-style agent busy UX (static contract).

Soft hue + strip layover; not heavy opaque modal. pointer-events block clicks.
"""

from __future__ import annotations

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "lca_wrench" / "static"


def _agent_hold_css_block(css: str) -> str:
    m = re.search(r"/\* Planet A #248.*?agent busy.*?\*/(.*)", css, re.S | re.I)
    assert m, "missing #248 agent busy CSS section"
    return m.group(1)


def test_hold_markup_is_comet_strip_not_modal():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert 'id="agentHold"' in html
    hold = html.split('id="agentHold"', 1)[1].split('<div class="toast"', 1)[0]
    assert "aria-modal" not in hold
    assert "agent-hold-hue" in hold
    assert "agent-hold-strip" in hold
    assert "agent-hold-card" not in hold


def test_hold_css_soft_hue_blocks_pointer_events():
    css = (STATIC / "app.css").read_text(encoding="utf-8")
    block = _agent_hold_css_block(css)
    assert ".agent-hold-hue" in block
    assert ".agent-hold-strip" in block
    assert "pointer-events:auto" in block.replace(" ", "") or "pointer-events: auto" in block
    assert "backdrop-filter" not in block
    assert "place-items:center" not in block.replace(" ", "").replace("place-items: center", "PLACE")
    # Soft tint — accent ≤ ~14% in color-mix (not 35% fg wall)
    assert re.search(r"color-mix\([^)]*var\(--accent\)\s+(\d+)%", block)
    pct = int(re.search(r"color-mix\([^)]*var\(--accent\)\s+(\d+)%", block).group(1))
    assert pct <= 14, f"hue too strong: {pct}%"


def test_sync_agent_hold_still_toggles_hidden():
    js = (STATIC / "js" / "main.js").read_text(encoding="utf-8")
    assert "function syncAgentHold(busy)" in js
    assert "el.hidden = !on" in js
    assert "agentHoldTitle" in js
