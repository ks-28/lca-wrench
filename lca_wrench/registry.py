"""Small JSON file next to the Brightway projects with what this app manages.

Keys: "copies" (working copies of projects), "models" (model databases per
project), "journal" (undo log per project).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import bw2data as bd


def path() -> Path:
    override = os.environ.get("LCA_WRENCH_REGISTRY")  # tests use their own file, never the user's
    if override:
        return Path(override)
    return Path(bd.projects._base_data_dir) / "lca-wrench.json"


def load() -> dict:
    p = path()
    if not p.exists() and not os.environ.get("LCA_WRENCH_REGISTRY"):
        p = p.with_name("werkbank.json")  # written before the rename to LCA Wrench; the next save moves it over
    if p.exists():
        try:
            reg = json.loads(p.read_text(encoding="utf-8"))
            reg.setdefault("copies", {})
            return reg
        except (OSError, json.JSONDecodeError):
            pass
    return {"copies": {}}


def save(reg: dict) -> None:
    p = path()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(reg, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)
