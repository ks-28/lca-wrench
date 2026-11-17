"""Characterization factors across elementary flow lists, through a flow mapping.

A project can hold data on two lists of elementary flows: ecoinvent's (biosphere3, also EXIOBASE as imported here)
and the EF 3.1 reference list (BAFU 2026 through sentier-brightway). A method is implemented on one of them: the
methods ecoinvent ships on biosphere3, sentier's EF 3.1 on ef-3.1-biosphere. On a product of the other list it finds
no factor and gives 0, which looks like a result.

The mapping "ecoinvent-3.11-biosphere-EF-3.1-biosphere" (randonneur_data, Chris Mutel and the UNEP GLAD mapping
task force, CC-BY 4.0; data/flowmaps) matches 9238 ecoinvent flows to EF 3.1 flows by UUID. With it, a method that
covers one list gets factors for the matched flows of the other: an EF flow takes the factor of the ecoinvent flows
matched to it (their mean), an ecoinvent flow the factor of its EF flow. Only flows of a list the method has no factor
on at all are filled, so a method's own factors (and its zeros) stay as they are; only pairs with the same unit count.

How well this works depends on the kind of impact. EF 3.1 is implemented on both lists in a project with ecoinvent's
LCIA methods and BAFU 2026, so each direction was checked against the native implementation on 7 to 8 products
(README): climate change, acidification, eutrophication, photochemical ozone, ionising radiation and land use agree
within a few per cent (mostly exactly) in both directions; ozone depletion only from EF to ecoinvent, mineral resources
only from ecoinvent to EF. Particulate matter (-5 to -25 %), toxicity, water use and energy resources (kg against
MJ) do not, so they are never filled. Topics as in overview.topic.

Applied in the calculation (engine.cvec, the cross-check, Monte Carlo), not written into the project. On by default,
can be switched off (registry "flowmap").
"""

from __future__ import annotations

import gzip
import json
import logging
import threading
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MAPPING = HERE / "data" / "flowmaps" / "ecoinvent-3.11-biosphere-EF-3.1-biosphere.json.gz"
SOURCE = ("ecoinvent 3.11 ↔ EF 3.1 (randonneur_data: Chris Mutel, UNEP GLAD mapping task force; CC-BY 4.0)")
TO_EF = frozenset({"climate", "acidification", "eutrophication", "smog", "radiation", "land", "minerals"})
TO_EI = frozenset({"climate", "acidification", "eutrophication", "smog", "radiation", "land", "ozone"})
_SAME_UNIT = {("m2*year", "m2*a"), ("m3*year", "m3*a")}

_lock = threading.RLock()
_pairs: list[tuple[str, str]] | None = None
_index: dict = {}  # project -> (stamp, Index)
_added: dict = {}  # (project, stamp, method, num_cfs) -> {flow id: factor}
_dbs: dict = {}  # (project, stamp, method, num_cfs) -> frozenset of databases with factors


def pairs() -> list[tuple[str, str]]:
    """(ecoinvent UUID, EF 3.1 UUID) of the mapping, same unit only. Empty when the file is missing or broken, e.g.
    a new version copied over an older folder without it: then no factors are mapped, but everything else works."""
    global _pairs
    if _pairs is None:
        try:
            rows = json.loads(gzip.decompress(MAPPING.read_bytes()))["replace"]
        except (OSError, ValueError, KeyError, EOFError) as e:
            logging.getLogger("lca_wrench").error(
                "Flow mapping not available (%s): %s. Calculating without it. Unpack LCA Wrench again into an "
                "empty folder to get it back.", MAPPING, e)
            _pairs = []
            return _pairs
        _pairs = [(r["source"]["uuid"], r["target"]["uuid"]) for r in rows
                  if float(r["target"].get("unit_scaling", 1.0)) == 1.0
                  and (r["source"].get("unit") == r["target"].get("unit_name")
                       or (r["source"].get("unit"), r["target"].get("unit_name")) in _SAME_UNIT)]
    return _pairs


def enabled() -> bool:
    from . import registry

    return registry.load().get("flowmap", True) is not False


def set_enabled(on: bool) -> None:
    from . import engine, registry

    reg = registry.load()
    reg["flowmap"] = bool(on)
    registry.save(reg)
    with _lock:
        _added.clear()
    engine.bump_all()


class Index:
    """Which database each node id belongs to, and the matched flows of the project's lists."""

    def __init__(self):
        import bw2data as bd
        from bw2data.backends import ActivityDataset as AD

        src = {s for s, _ in pairs()}
        tgt = {t for _, t in pairs()}
        names = sorted(bd.databases)
        pos = {n: i for i, n in enumerate(names)}
        ids, dbi = [], []
        code_id: dict[str, dict[str, int]] = {}
        n_src: dict[str, int] = {}
        n_tgt: dict[str, int] = {}
        size: dict[str, int] = {}
        for i, code, db in AD.select(AD.id, AD.code, AD.database).tuples().iterator():
            if db not in pos:
                continue
            ids.append(i)
            dbi.append(pos[db])
            size[db] = size.get(db, 0) + 1
            if code in src or code in tgt:
                code_id.setdefault(db, {})[code] = i
                n_src[db] = n_src.get(db, 0) + (code in src)
                n_tgt[db] = n_tgt.get(db, 0) + (code in tgt)
        order = np.argsort(np.array(ids, dtype=np.int64))
        self.ids = np.array(ids, dtype=np.int64)[order]
        self.dbi = np.array(dbi, dtype=np.int32)[order]
        self.names = names
        # a list on one side of the mapping: most of its flows matched, or most of the mapping's side found in it
        ei = [db for db in names if (k := n_src.get(db, 0)) and k >= max(1, 0.5 * min(size[db], len(src)))]
        ef = [db for db in names if (k := n_tgt.get(db, 0)) and k >= max(1, 0.5 * min(size[db], len(tgt)))]
        self.links = []  # (ecoinvent list, EF list, {ei id: ef id}, {ef id: [ei ids]})
        for a in ei:
            for b in ef:
                if a == b:
                    continue
                to_ef, to_ei = {}, {}
                ca, cb = code_id.get(a, {}), code_id.get(b, {})
                for s, t in pairs():
                    if s in ca and t in cb:
                        to_ef[ca[s]] = cb[t]
                        to_ei.setdefault(cb[t], []).append(ca[s])
                if to_ef:
                    self.links.append((a, b, to_ef, to_ei))

    def dbs_of(self, node_ids) -> set[str]:
        node_ids = np.asarray(node_ids, dtype=np.int64)
        if not len(node_ids) or not len(self.ids):
            return set()
        k = np.searchsorted(self.ids, node_ids)
        k = np.clip(k, 0, len(self.ids) - 1)
        hit = self.ids[k] == node_ids
        return {self.names[i] for i in np.unique(self.dbi[k[hit]])}


def _stamp() -> tuple:
    """The databases of the project, by name: flow lists change with them (editing a model does not change them)."""
    import bw2data as bd

    return tuple(sorted(bd.databases))


def index() -> Index:
    import bw2data as bd

    p = bd.projects.current
    st = _stamp()
    with _lock:
        hit = _index.get(p)
        if hit is None or hit[0] != st:
            hit = (st, Index())
            _index[p] = hit
        return hit[1]


def _key(method: tuple) -> tuple:
    import bw2data as bd

    return (bd.projects.current, _stamp(), tuple(method), (bd.methods.get(tuple(method)) or {}).get("num_cfs"))


def method_dbs(method: tuple) -> frozenset[str]:
    """The databases (flow lists) the method has factors on."""
    from . import engine

    k = _key(method)
    with _lock:
        if k not in _dbs:
            _dbs[k] = frozenset(index().dbs_of(list(engine.method_cfs(tuple(method)))))
        return _dbs[k]


def _topic(method: tuple) -> str:
    from . import overview

    return overview.topic(tuple(method))


def fills(method: tuple) -> list[tuple[str, str]]:
    """(from list, to list) for each list the method gets factors on through the mapping."""
    if not enabled():
        return []
    have, tp = method_dbs(method), _topic(method)
    out = []
    for a, b, _, _ in index().links:
        if a in have and b not in have and tp in TO_EF:
            out.append((a, b))
        if b in have and a not in have and tp in TO_EI:
            out.append((b, a))
    return out


def added(method: tuple) -> dict[int, float]:
    """The factors the method gets through the mapping, per flow id (empty when none or switched off)."""
    from . import engine

    if not enabled():
        return {}
    k = _key(method)
    with _lock:
        if k in _added:
            return _added[k]
    out: dict[int, float] = {}
    todo = fills(method)
    if todo:
        cf = engine.method_cfs(tuple(method))
        for a, b, to_ef, to_ei in index().links:
            if (a, b) in todo:  # ecoinvent factors onto EF flows: the mean of the matched ecoinvent flows
                for ef_id, ei_ids in to_ei.items():
                    vals = [cf[i] for i in ei_ids if i in cf]
                    if vals:
                        out[ef_id] = sum(vals) / len(vals)
            if (b, a) in todo:  # EF factors onto ecoinvent flows
                for ei_id, ef_id in to_ef.items():
                    if ef_id in cf:
                        out[ei_id] = cf[ef_id]
    with _lock:
        _added[k] = out
    return out


def addition(method: tuple, flow_ids) -> np.ndarray | None:
    """The mapped factors over `flow_ids` (a matrix's biosphere rows), to add to the method's own; None if none."""
    add = added(method)
    if not add:
        return None
    vec = np.fromiter((add.get(int(f), 0.0) for f in flow_ids), dtype=float, count=len(flow_ids))
    return vec if vec.any() else None


def characterized() -> frozenset[str]:
    """The flow lists any method of the project has factors on. A list none has (BAFU's residual flows) cannot be
    missing from one method."""
    import bw2data as bd

    k = (bd.projects.current, _stamp(), "*", len(bd.methods))
    with _lock:
        if k not in _dbs:
            _dbs[k] = frozenset().union(*(method_dbs(m) for m in bd.methods)) if len(bd.methods) else frozenset()
        return _dbs[k]


def coverage(method: tuple, lists: set[str]) -> tuple[str, list[str]]:
    """How the method covers the flow lists a result draws on: "native", "mapped" (some through the mapping) or
    "missing", with the lists it has no factor for (only lists some method has factors on)."""
    lists = set(lists) & characterized()
    have = method_dbs(method)
    mapped = {b for _, b in fills(method)}
    missing = sorted(lists - have - mapped)
    if missing:
        return "missing", missing
    return ("mapped" if lists & mapped - have else "native"), []


def info() -> dict:
    """For the UI: is it on, and which lists of this project it links."""
    try:
        links = [[a, b] for a, b, _, _ in index().links]
    except Exception:  # noqa: BLE001 - an unusual project must not break the state
        links = []
    return {"enabled": enabled(), "links": links, "source": SOURCE}
