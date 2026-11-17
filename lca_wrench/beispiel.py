"""One-click example: a simplified e-bike model plus a comparison per kilometre.

The amounts are rough teaching values, not a validated dataset. The model is
built only from BAFU:2025 processes and lands in its own model database.
"""

from __future__ import annotations

import bw2data as bd
from bw2data.backends.schema import ActivityDataset as AD

from . import models, setups
from .i18n import _, msg

BG = "BAFU-2025-v2"

# (name, location) of the BAFU processes used
P = {
    "alu": ("Aluminium, production mix, wrought alloy, at plant", "RER"),
    "extrusion": ("Section bar extrusion, aluminium", "RER"),
    "strom": ("Electricity, low voltage, at grid", "CH"),
    "akku": ("Battery, Li-ion, NMC111, rechargeable, prismatic", "GLO"),
    "motor": ("Electric motor, for electric scooter", "RER"),
    "stahl": ("Steel, low-alloyed, at plant", "RER"),
    "gummi": ("Synthetic rubber, at plant", "RER"),
    "lkw": ("Transport, freight, lorry, 7.5t-16t gross weight, fleet average", "CH"),
    "ebike_bafu": ("Transport, Bicycle, electric (<25 km/h), NCA battery, 2020", "CH"),
    "velo_bafu": ("Transport, Bicycle, conventional, urban, 2020", "CH"),
    "auto_bafu": ("Transport, passenger car, fleet average", "CH"),
}


_ids: dict = {}


def _lookup() -> dict:
    """Ids of the BAFU processes the example needs (cached per project, one query)."""
    project = bd.projects.current
    if project not in _ids:
        found = {}
        if BG in bd.databases:
            names = [n for n, _ in P.values()]
            rows = AD.select(AD.id, AD.name, AD.location).where(AD.database == BG, AD.name << names).tuples()
            for nid, name, loc in rows:
                found.setdefault((name, loc), nid)
        _ids[project] = {k: found.get(v) for k, v in P.items()}
    return _ids[project]


def available() -> bool:
    return BG in bd.databases and all(v is not None for v in _lookup().values())


def create() -> dict:
    if not available():
        raise ValueError(_("Das Beispiel braucht die Datenbank BAFU-2025-v2 in diesem Projekt."))
    ids = dict(_lookup())
    # names in the language of the UI at the time the example is made
    note = _("Vereinfachtes Lehrbeispiel von LCA Wrench mit geschätzten Mengen. Kein validierter Datensatz.")
    name, n = _("Beispiel – E-Bike"), 1
    while name in bd.databases:
        n += 1
        name = _("Beispiel – E-Bike ({n})", n=n)
    start = models.journal_length()
    models.create_database(name)

    def proc(title, unit, inputs):
        pid = models.create_process(name, title, unit, "CH", comment=note)
        for key, amount in inputs:
            models.add_exchange(pid, ids.get(key, key), amount)
        return pid

    rahmen = proc(_("Rahmen, Aluminium"), "unit", [("alu", 2.4), ("extrusion", 2.4), ("strom", 4.0)])
    akku = proc(_("Akku 500 Wh"), "unit", [("akku", 2.9)])
    antrieb = proc(_("Antrieb, Nabenmotor"), "unit", [("motor", 3.2)])
    ebike = proc(_("E-Bike, montiert"), "unit", [(rahmen, 1), (akku, 1), (antrieb, 1), ("stahl", 7.0),
                                                  ("gummi", 1.6), ("strom", 12.0), ("lkw", 1.2)])
    fahrt = proc(_("Fahrt mit dem E-Bike"), "kilometer", [(ebike, 1 / 15000), (akku, 1 / 30000), ("strom", 0.011)])

    setup = _("Beispiel – pro Kilometer ({name})", name=name) if n > 1 else _("Beispiel – pro Kilometer")
    methods = [m for m in [("Werkbank", "Klimawandel", "kg CO2-eq, abgeleitet aus UBP 2021"),
                           ("Werkbank", "Umweltbelastungspunkte gesamt", "UBP 2021"),
                           ("Ecological Scarcity 2021", "Main air pollutants and PM"),
                           ("Ecological Scarcity 2021", "Mineral resources")] if m in bd.methods]
    fus = [{"id": fahrt, "amount": 1}, {"id": ids["ebike_bafu"], "amount": 1},
           {"id": ids["velo_bafu"], "amount": 1}, {"id": ids["auto_bafu"], "amount": 1}]
    if setup in bd.calculation_setups:
        setups.delete(setup)
    setups.save(setup, fus, [list(m) for m in methods])
    models.squash_journal(start, msg("Beispiel «{name}» angelegt", name=name), {"op": "delete_database", "name": name, "setup": setup})
    return {"database": name, "process": str(fahrt), "setup": setup}
