"""Rebuild the list of a project's databases (databases.json) from the data in the project.

bw2data keeps the list of a project's databases, with backend and dependencies, in databases.json. When writing it
fails, bw2data's "atomic" write still swaps the new file in: databases.json is then empty, and neither Brightway nor
the Activity Browser nor LCA Wrench can open the project. A premise run met that (see premise_worker.py). The data
themselves are untouched: the activities and exchanges in lci/databases.db, the matrices in processed/. From them:

- every database with activities in lci/databases.db, and the empty model databases LCA Wrench made in the project
- backend "iotable" (EXIOBASE) when its exchanges live only in its processed datapackage, else "sqlite"
- depends: the databases its exchanges come from (iotable: those of the rows of its matrices)
- number, searchable, modified; sqlite databases are processed again (matrices, geocollections, processed)
- LCA Wrench's tags: scenario for "<source> <model> <pathway> <year>" (premise), mrio for iotable

Lost are only descriptive fields such as "format". The broken file is kept as databases.json.broken-<time>.

    python -m lca_wrench.repair "<project>"                       shows what it would write
    python -m lca_wrench.repair "<project>" --write               writes it
    python -m lca_wrench.repair "<project>" --write --drop "<db>"  and removes a database (e.g. left by a failed run)
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sqlite3
import sys
import zipfile
from pathlib import Path

SCENARIO = re.compile(r"^(?P<source>.+) (?P<model>remind|remind-eu|image|message|tiam-ucl|gcam|witch) "
                      r"(?P<pathway>\S+) (?P<year>\d{4})$")


def project_dir(name: str) -> Path | None:
    """The folder of a project, without opening it (opening reads the broken list); None when there is none."""
    import bw2data as bd
    from bw2data.project import ProjectDataset

    ds = ProjectDataset.get_or_none(ProjectDataset.name == name)
    return Path(bd.projects._project_dir(ds)) if ds is not None else None


def listing_ok(folder: Path) -> bool:
    """databases.json can be read (a project without one yet is fine too: Brightway creates it)."""
    f = folder / "databases.json"
    if not f.exists():
        return True
    try:
        json.loads(f.read_bytes())
        return True
    except (OSError, ValueError):
        return False


def damaged(name: str) -> bool:
    """The project exists, but its list of databases cannot be read: opening it would fail."""
    folder = project_dir(name)
    return folder is not None and not listing_ok(folder)


def _processed(folder: Path, name: str) -> Path:
    from bw_processing import clean_datapackage_name, safe_filename  # as bw2data names them (data_store.py)

    return folder / "processed" / clean_datapackage_name(safe_filename(name) + ".zip")


def _package_rows(path: Path) -> tuple[dict, set[int]]:
    """Metadata of a processed datapackage and the node ids in the rows of its matrices."""
    import numpy as np

    with zipfile.ZipFile(path) as z:
        meta = json.loads(z.read("datapackage.json"))
        ids: set[int] = set()
        for r in meta.get("resources", []):
            if r.get("kind") == "indices" or r["path"].endswith(".indices.npy"):
                with z.open(r["path"]) as f:
                    arr = np.load(f, allow_pickle=False)
                ids.update(int(x) for x in np.unique(arr["row"]))
    return {k: v for k, v in meta.items() if k != "resources"}, ids


def survey(folder: Path, project: str) -> dict[str, dict]:
    """What the data in the project say about its databases (read-only)."""
    con = sqlite3.connect(f"file:{folder / 'lci' / 'databases.db'}?mode=ro", uri=True)
    try:
        counts = dict(con.execute("SELECT database, COUNT(*) FROM activitydataset GROUP BY database"))
        links: dict[str, set[str]] = {}
        for out, inp in con.execute("SELECT DISTINCT output_database, input_database FROM exchangedataset"):
            links.setdefault(out, set()).add(inp)
        db_of = None
        found = {}
        for name, n in sorted(counts.items()):
            info = {"backend": "sqlite", "number": n, "depends": sorted(links.get(name, set()) - {name})}
            p = _processed(folder, name)
            if name not in links and p.is_file():
                meta, rows = _package_rows(p)
                if "database_dependencies" not in meta and rows:  # an IO table: exchanges only in the package
                    if db_of is None:
                        db_of = dict(con.execute("SELECT id, database FROM activitydataset"))
                    info.update(backend="iotable", depends=sorted({db_of[i] for i in rows if i in db_of} - {name}))
            found[name] = info
    finally:
        con.close()
    try:
        from . import registry

        for name in registry.load().get("models", {}).get(project, []):
            found.setdefault(name, {"backend": "sqlite", "number": 0, "depends": []})
    except Exception:  # noqa: BLE001 - the registry is a bonus
        pass
    for name, info in found.items():
        m = SCENARIO.match(name)
        if info["backend"] == "iotable":
            info["lca_wrench"] = {"kind": "mrio"}
        elif m and m["source"] in found:
            info["lca_wrench"] = {"kind": "scenario", "scenario": {
                "model": m["model"], "pathway": m["pathway"], "year": int(m["year"]), "source": m["source"]}}
    return found


def rebuild(project: str, write: bool = False, drop: tuple[str, ...] = (), out=print) -> dict[str, dict]:
    import bw2data as bd

    folder = project_dir(project)
    if folder is None:
        raise SystemExit(f"No project «{project}» in {bd.projects._base_data_dir}")
    out(f"Project «{project}»: {folder}")
    out("databases.json can be read: nothing to repair." if listing_ok(folder) else "databases.json cannot be read.")
    found = survey(folder, project)
    missing = [d for d in drop if d not in found]
    if missing:
        raise SystemExit(f"Not in the project: {', '.join(missing)}")
    for name, info in found.items():
        tag = (info.get("lca_wrench") or {}).get("kind", "")
        out(f"  {'DROP ' if name in drop else ''}{name}: {info['number']} activities, {info['backend']}"
            f"{', ' + tag if tag else ''}, depends on {', '.join(info['depends']) or '–'}")
    if not write:
        out("Nothing written (add --write).")
        return found
    if listing_ok(folder):
        raise SystemExit("databases.json is readable: not overwritten.")
    now = datetime.datetime.now()
    listing = folder / "databases.json"
    os.replace(listing, folder / f"databases.json.broken-{now:%Y%m%d-%H%M%S}")
    meta = {name: {"backend": info["backend"], "depends": info["depends"], "number": info["number"],
                   "searchable": True, "modified": now.isoformat(), "dirty": info["backend"] == "sqlite",
                   **({"lca_wrench": info["lca_wrench"]} if "lca_wrench" in info else {})}
            for name, info in found.items()}
    for name in drop:  # registered for now, so bw2data removes it completely below
        meta[name]["dirty"] = False
    tmp = listing.with_name("databases.json.lca-wrench-tmp")
    tmp.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, listing)
    out("databases.json written.")

    bd.projects.set_current(project, update=False)
    for name in drop:
        del bd.databases[name]
        out(f"  {name}: removed")
    for name in sorted(bd.databases):
        if bd.databases[name].get("backend") == "sqlite":
            out(f"  {name}: processing …")
            bd.Database(name).process()
            bd.databases[name]["dirty"] = False
    bd.databases.flush()
    out("Done.")
    return found


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project")
    ap.add_argument("--write", action="store_true", help="write the rebuilt list (otherwise only show it)")
    ap.add_argument("--drop", action="append", default=[], help="remove this database (repeatable)")
    a = ap.parse_args(argv)
    rebuild(a.project, write=a.write, drop=tuple(a.drop))
    return 0


if __name__ == "__main__":
    sys.exit(main())
