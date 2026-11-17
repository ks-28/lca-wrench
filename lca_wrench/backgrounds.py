"""Which background databases a calculation uses: one database, or several combined.

A project can hold several background databases: BAFU and ecoinvent, two ecoinvent versions, premise scenarios of
ecoinvent ("ecoinvent 3.10, REMIND SSP2-PkBudg1000, 2040") or an input-output table like EXIOBASE. Two ways to
calculate with them:

- **single** (the usual way): one background database. The models' inputs from another background database are
  taken from their counterpart in the chosen one, so the same model can be calculated on ecoinvent today and on a
  premise scenario for 2040 without copying it.
- **combined**: several background databases at once, e.g. ecoinvent for the processes and EXIOBASE for purchased
  services (hybrid LCA), or BAFU next to ecoinvent.

The counterpart of a dataset is the one with the same code (premise and newer ecoinvent versions keep the codes),
otherwise the one with the same name, reference product, location and unit, otherwise the same with the nearest
location around it (DE → RER → GLO → RoW). An input without counterpart keeps its database, which then joins the
calculation; the result says so. The choice is kept per project in LCA Wrench's own registry, not in the project.

Without a choice: every background database except scenarios and input-output tables, which is how LCA Wrench
calculated before (a project with BAFU 2025 and 2026 has both).
"""

from __future__ import annotations

import re

import bw2data as bd
from bw2data.backends.schema import ActivityDataset as AD

from . import regions, registry

KINDS = ("lci", "scenario", "mrio")
# premise names its databases "ecoinvent_cutoff_3.10_remind_SSP2-NPi_2040"
_SCENARIO = re.compile(r"(remind|image|message|tiam|gcam|witch).*(ssp\d|base|npi|ndc|rcp|pkbudg|static).*\b(20\d\d|2100)\b", re.I)


def kind(name: str) -> str:
    """lci (process data), scenario (premise) or mrio (input-output table, EXIOBASE)."""
    meta = bd.databases.get(name) or {}
    tag = (meta.get("lca_wrench") or {}).get("kind")
    if tag in KINDS:
        return tag
    if meta.get("backend") == "iotable" or "exiobase" in name.lower() or str(meta.get("format", "")).startswith("EXIOBASE"):
        return "mrio"
    if _SCENARIO.search(name) or meta.get("premise"):
        return "scenario"
    return "lci"


def _backgrounds(roles: dict) -> list[str]:
    return sorted(n for n, r in roles.items() if r == "background")


def default(roles: dict) -> list[str]:
    bgs = _backgrounds(roles)
    plain = [n for n in bgs if kind(n) == "lci"]
    return plain or bgs[:1]


def choice(roles: dict, project: str | None = None) -> dict:
    """{"mode": "single"|"combined"|"auto", "databases": [...]}: what the user chose, checked against the project."""
    project = project or bd.projects.current
    bgs = set(_backgrounds(roles))
    saved = (registry.load().get("backgrounds") or {}).get(project)
    if saved:
        dbs = [d for d in saved.get("databases", []) if d in bgs]
        if dbs:
            mode = saved.get("mode") if saved.get("mode") in ("single", "combined") else "combined"
            return {"mode": mode, "databases": dbs[:1] if mode == "single" else dbs}
    return {"mode": "auto", "databases": default(roles)}


def active(roles: dict) -> list[str]:
    return choice(roles)["databases"]


def set_choice(mode: str, databases: list[str], roles: dict) -> dict:
    from .i18n import _

    bgs = set(_backgrounds(roles))
    dbs = [d for d in dict.fromkeys(databases or []) if d in bgs]
    if mode not in ("single", "combined", "auto"):
        raise ValueError(_("Unbekannte Wahl für die Hintergrunddaten."))
    if mode != "auto" and not dbs:
        raise ValueError(_("Bitte mindestens eine Hintergrund-Datenbank wählen."))
    if mode == "single" and len(dbs) != 1:
        raise ValueError(_("Bitte genau eine Hintergrund-Datenbank wählen."))
    reg = registry.load()
    store = reg.setdefault("backgrounds", {})
    if mode == "auto":
        store.pop(bd.projects.current, None)
    else:
        store[bd.projects.current] = {"mode": mode, "databases": dbs}
    registry.save(reg)
    return choice(roles)


def removable(name: str) -> bool:
    """A database LCA Wrench added itself (premise scenario, EXIOBASE): only those can be removed again in the app.
    ecoinvent, BAFU and anything from elsewhere stay as they are."""
    return ((bd.databases.get(name) or {}).get("lca_wrench") or {}).get("kind") in ("scenario", "mrio")


def forget(name: str) -> None:
    """Take a removed database out of the saved choice of the current project."""
    reg = registry.load()
    saved = (reg.get("backgrounds") or {}).get(bd.projects.current)
    if not saved or name not in saved.get("databases", []):
        return
    saved["databases"] = [d for d in saved["databases"] if d != name]
    if not saved["databases"]:
        del reg["backgrounds"][bd.projects.current]
    registry.save(reg)


def options(roles: dict) -> list[dict]:
    out = []
    for n in _backgrounds(roles):
        meta = bd.databases.get(n) or {}
        out.append({"name": n, "kind": kind(n), "scenario": (meta.get("lca_wrench") or {}).get("scenario"),
                    "removable": removable(n)})
    return out


# ---------- counterparts ----------

def _product(d: dict) -> str:
    return re.sub(r"\s*\{[^{}]*\}\s*$", "", d.get("reference product") or "")


def _index(dbs: list[str], names: set[str]) -> tuple[dict, dict]:
    """Datasets of `dbs` with one of these names: by code, and by (name, product, unit) → {location: id}."""
    by_code, by_key = {}, {}
    names = sorted(n for n in names if n)
    for i in range(0, len(names), 500):
        q = AD.select(AD.id, AD.database, AD.code, AD.name, AD.location, AD.data).where(
            (AD.database << dbs) & (AD.name << names[i:i + 500]))
        for nid, _db, code, name, loc, data in q.tuples():
            by_code.setdefault(code, (nid, name, _product(data)))
            by_key.setdefault((name, _product(data), data.get("unit")), {}).setdefault(loc, nid)
    return by_code, by_key


def _match(src: dict, by_code: dict, by_key: dict) -> int | None:
    hit = by_code.get(src["code"])
    if hit and (hit[1] == src["name"] or hit[2] == src["product"]):
        return hit[0]
    locs = by_key.get((src["name"], src["product"], src["unit"]))
    if not locs:
        return None
    if src["location"] in locs:
        return locs[src["location"]]
    for loc in regions.chain(src["location"])[1:]:
        if loc in locs:
            return locs[loc]
    return None


def _sources(where) -> list[dict]:
    return [{"id": nid, "db": db, "code": code, "name": name, "location": loc, "product": _product(data),
             "unit": data.get("unit")}
            for nid, db, code, name, loc, data in AD.select(AD.id, AD.database, AD.code, AD.name, AD.location, AD.data)
            .where(where).tuples()]


def counterparts_by_key(refs: dict[str, set], targets: list[str]) -> tuple[dict, dict]:
    """{database: {codes}} → ({(database, code): id in targets}, {database: number without counterpart})."""
    srcs = []
    for db, codes in refs.items():
        codes = sorted(codes)
        for i in range(0, len(codes), 500):
            srcs += _sources((AD.database == db) & (AD.code << codes[i:i + 500]))
    by_code, by_key = _index(targets, {s["name"] for s in srcs})
    alias, unmatched = {}, {}
    for s in srcs:
        m = _match(s, by_code, by_key)
        if m is None:
            unmatched[s["db"]] = unmatched.get(s["db"], 0) + 1
        else:
            alias[(s["db"], s["code"])] = m
    return alias, unmatched


def counterparts(node_ids: list[int], targets: list[str]) -> dict[int, int]:
    """{node id: id of the same dataset in `targets`} for nodes outside them; nodes without counterpart left out."""
    ids = [int(i) for i in node_ids]
    srcs = []
    for i in range(0, len(ids), 500):
        srcs += _sources((AD.id << ids[i:i + 500]) & ~(AD.database << targets))
    by_code, by_key = _index(targets, {s["name"] for s in srcs})
    out = {}
    for s in srcs:
        m = _match(s, by_code, by_key)
        if m is not None:
            out[s["id"]] = m
    return out
