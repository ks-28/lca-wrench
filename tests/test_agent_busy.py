"""#248 — agent busy hold: heartbeat + stale TTL (crash must not stick forever)."""

from __future__ import annotations

import time

import pytest

from lca_wrench import service as s


@pytest.fixture(autouse=True)
def _reset_agent():
    s.AGENT["busy"] = False
    s.AGENT["mutations"] = 0
    s.AGENT["what"] = ""
    s.AGENT["beat"] = 0.0
    yield
    s.AGENT["busy"] = False
    s.AGENT["beat"] = 0.0


def test_busy_expires_without_heartbeat(monkeypatch):
    monkeypatch.setattr(s, "AGENT_BUSY_TTL_S", 0.05)
    assert s.set_agent_busy(True)["busy"] is True
    assert s.poll()["agent_busy"] is True
    time.sleep(0.06)
    assert s.poll()["agent_busy"] is False
    assert s.AGENT["busy"] is False


def test_busy_heartbeat_extends_hold(monkeypatch):
    monkeypatch.setattr(s, "AGENT_BUSY_TTL_S", 0.1)
    s.set_agent_busy(True)
    time.sleep(0.06)
    s.set_agent_busy(True)  # MCP heartbeat = busy:true again
    time.sleep(0.06)
    assert s.poll()["agent_busy"] is True
    s.set_agent_busy(False)
    assert s.poll()["agent_busy"] is False


def test_clear_busy_immediate():
    s.set_agent_busy(True)
    assert s.poll()["agent_busy"] is True
    s.set_agent_busy(False)
    assert s.poll()["agent_busy"] is False
