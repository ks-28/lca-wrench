"""Calculation setups: several products times several methods.

Stored in bw2data's calculation_setups, in the same format the Activity
Browser uses ({"inv": [{key: amount}], "ia": [method]}), so setups are shared
between both programs.
"""

from __future__ import annotations

import time

import bw2data as bd

from . import analysis, completion, models
from .i18n import _


def list_setups() -> list[dict]:
    out = []
    for name in sorted(bd.calculation_setups):
        cs = bd.calculation_setups[name]
        out.append({"name": name, "fus": len(cs.get("inv", [])), "methods": len(cs.get("ia", []))})
    return out


def _resolve(key) -> int | None:
    try:
        if isinstance(key, int):
            return bd.get_node(id=key).id
        return bd.get_node(database=key[0], code=key[1]).id
    except (bd.errors.UnknownObject, TypeError, IndexError):
        return None


def get(name: str) -> dict:
    if name not in bd.calculation_setups:
        raise KeyError(_("Die Rechnung «{name}» gibt es nicht.", name=name))
    cs = bd.calculation_setups[name]
    fus, missing = [], 0
    ids = []
    for fu in cs.get("inv", []):
        for key, amount in fu.items():
            nid = _resolve(key)
            if nid is None:
                missing += 1
                continue
            ids.append(nid)
            fus.append({"id": str(nid), "amount": float(amount)})
    info = analysis.node_info(ids)
    for fu in fus:
        fu.update({k: info[int(fu["id"])][k] for k in ("name", "location", "unit", "database")})
    methods = [list(m) for m in cs.get("ia", []) if tuple(m) in bd.methods]
    return {"name": name, "fus": fus, "methods": methods, "missing": missing,
            "missing_methods": len(cs.get("ia", [])) - len(methods)}


def save(name: str, fus: list[dict], methods: list[list[str]], old_name: str | None = None) -> str:
    name = (name or "").strip()
    if not name:
        raise ValueError(_("Bitte der Rechnung einen Namen geben."))
    if name != old_name and name in bd.calculation_setups:
        raise ValueError(_("Eine Rechnung «{name}» gibt es schon.", name=name))
    inv = []
    for fu in fus:
        node = bd.get_node(id=int(fu["id"]))
        inv.append({node.key: float(fu["amount"])})
    ia = [tuple(m) for m in methods if tuple(m) in bd.methods]
    cs = {"inv": inv, "ia": ia}
    if old_name and old_name in bd.calculation_setups:
        prev = bd.calculation_setups[old_name]
        for k, v in prev.items():
            if k not in ("inv", "ia", "inv_active", "ia_active"):
                cs[k] = v
        if old_name != name:
            del bd.calculation_setups[old_name]
    bd.calculation_setups[name] = cs
    bd.calculation_setups.serialize()
    return name


def delete(name: str) -> None:
    if name in bd.calculation_setups:
        del bd.calculation_setups[name]
        bd.calculation_setups.serialize()


def calculate(fus: list[dict], methods: list[tuple]) -> dict:
    """Score table for products times methods; live for models, exact for everything."""
    S = models.system()
    t = time.perf_counter()
    pairs = [(int(f["id"]), float(f["amount"])) for f in fus]
    table = analysis.score_table(S, pairs, [tuple(m) for m in methods])
    seconds = time.perf_counter() - t
    info = analysis.node_info(i for i, _ in pairs)
    return {
        "fus": [{**info.get(i, {"id": str(i), "name": "?"}), "amount": a} for i, a in pairs],
        "methods": [{"id": list(m), "unit": analysis.short_unit(bd.methods[tuple(m)].get("unit")),
                     "completed": len(completion.added(tuple(m)))} for m in methods],
        "scores": table,  # [method][fu]
        "seconds": seconds,
    }
