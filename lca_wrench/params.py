"""Parameters and formulas as in the Activity Browser, stored in Brightway's own tables (parameters.db).

Three scopes: project (all databases), database (one own model) and process (one process of an own model, group
"database:code" as bw2io names it). Formulas of parameters and of exchanges use the names visible in their scope
(process -> database -> project). Brightway writes the result of a formula into the exchange amount, so the live
engine needs nothing special.

Two deliberate differences to Brightway's own `parameters.recalculate()`:
- Only the project and the own models are recalculated. The global call would also rewrite parameterized exchanges of
  background databases (ecoinvent carries some), which LCA Wrench never changes.
- Every change is first evaluated in memory, together with all other parameters and exchange formulas of the own
  models. Only if nothing is missing, circular or not a number is it written. Brightway itself stores the result of a
  broken exchange formula (None) as the amount without complaint.
Each change is one undo step: the managed state before it is kept and restored as a whole.
"""

from __future__ import annotations

import io
import json
import keyword
import math
import re

import asteval
import bw2data as bd
from bw2data.backends.proxies import Exchange
from bw2data.backends.schema import ExchangeDataset
from bw2data.parameters import (ActivityParameter, DatabaseParameter, Group, GroupDependency, ParameterizedExchange,
                                 ProjectParameter, parameters)
from bw2parameters import ParameterSet

from . import engine, models
from .i18n import _, msg

DUMMY = "__dummy_"
_BUILTINS = set(asteval.Interpreter().symtable)
_NUMBER = re.compile(r"^\s*[-+]?(\d+([.,]\d*)?|[.,]\d+)([eE][-+]?\d+)?\s*$")


def group_of(database: str, code: str) -> str:
    return f"{database}:{code}"


# ---------- reading ----------

def _rows(model):
    return {o.name: {"amount": o.amount, "formula": o.formula, "data": dict(o.data or {})} for o in model}


def state() -> dict:
    """Everything LCA Wrench manages: project parameters, parameters of own models and their processes, and the
    parameterized exchanges of those processes."""
    mdbs = sorted(models.model_databases())
    groups = {}
    for ap in ActivityParameter.select().where(ActivityParameter.database << mdbs):
        g = groups.setdefault(ap.group, {"database": ap.database, "code": ap.code, "params": {}})
        g["params"][ap.name] = {"amount": ap.amount, "formula": ap.formula, "data": dict(ap.data or {})}
    exchanges = {}
    for pe in ParameterizedExchange.select().where(ParameterizedExchange.group << list(groups)):
        try:
            ed = ExchangeDataset.get_by_id(pe.exchange)
        except ExchangeDataset.DoesNotExist:
            continue
        exchanges[pe.exchange] = {"group": pe.group, "formula": pe.formula, "amount": ed.data.get("amount"),
                                  "original_amount": ed.data.get("original_amount")}
    return {"project": _rows(ProjectParameter.select()),
            "database": {db: _rows(DatabaseParameter.select().where(DatabaseParameter.database == db)) for db in mdbs},
            "groups": groups, "exchanges": exchanges}


# ---------- checking ----------

def _interpreter() -> asteval.Interpreter:
    """The same interpreter Brightway evaluates formulas with, but quiet: errors are read from `.error`."""
    return asteval.Interpreter(writer=io.StringIO(), err_writer=io.StringIO())


def _formula_error(formula: str, symbols: dict) -> str | None:
    """None if `formula` evaluates to a finite number with `symbols`, else the reason."""
    interp = _interpreter()
    try:
        names = asteval.get_ast_names(interp.parse(formula))
    except Exception as e:  # syntax
        return _("Formel «{formula}» ist nicht lesbar: {error}", formula=formula, error=e)
    missing = sorted(set(names) - set(symbols) - _BUILTINS)
    if missing:
        return _("Formel «{formula}»: unbekannter Name {names}", formula=formula, names=", ".join(missing))
    interp.symtable.update(symbols)
    value = interp(formula)
    if interp.error or not isinstance(value, (int, float)) or not math.isfinite(value):
        return _("Formel «{formula}» ergibt keine Zahl.", formula=formula)
    return None


def _evaluate(st: dict) -> dict:
    """Values of every parameter and exchange formula in `st`, or ValueError with the first problem."""
    def run(params: dict, static: dict, where: str) -> dict:
        data = {n: {"amount": p["amount"] if p["amount"] is not None else 0, **({"formula": p["formula"]} if p["formula"] else {})}
                for n, p in params.items() if not n.startswith(DUMMY)}
        for n, p in data.items():
            if "formula" in p:
                err = _formula_error(p["formula"], {**static, **{k: 1.0 for k in data}})
                if err:
                    raise ValueError(_("{where}, Parameter «{name}»: {error}", where=where, name=n, error=err))
        try:
            return ParameterSet(data, static).evaluate()
        except Exception as e:
            raise ValueError(_("{where}: {error}", where=where, error=e)) from None

    P = run(st["project"], {}, _("Projekt"))
    D = {db: {**P, **run(params, P, _("Modell «{name}»", name=db))} for db, params in st["database"].items()}
    out = {"project": P, "database": D, "groups": {}, "exchanges": {}}
    for g, grp in st["groups"].items():
        base = D.get(grp["database"], P)
        out["groups"][g] = {**base, **run(grp["params"], base, _("Prozess-Parameter"))}
    for exc_id, e in st["exchanges"].items():
        syms = out["groups"].get(e["group"])
        if syms is None:
            continue
        err = _formula_error(e["formula"], syms)
        if err:
            raise ValueError(err)
        interp = _interpreter()
        interp.symtable.update(syms)
        out["exchanges"][exc_id] = float(interp(e["formula"]))
    return out


# ---------- writing ----------

def _recalculate() -> None:
    """Recalculate the project and the own models (not the background, see module docstring)."""
    mdbs = models.model_databases()
    if ProjectParameter.expired():
        ProjectParameter.recalculate()
    for db in mdbs:
        if DatabaseParameter.expired(db):
            DatabaseParameter.recalculate(db)
    for g in Group.select().where(Group.fresh == False):  # noqa: E712 (peewee)
        db = ActivityParameter.select(ActivityParameter.database).where(ActivityParameter.group == g.name).scalar()
        if db in mdbs:
            ActivityParameter.recalculate(g.name)
    for db in mdbs:
        bd.databases.set_dirty(db)
    engine.bump_foreground(bd.projects.current)


def _write(st: dict) -> None:
    """Make the managed state equal to `st` (rows of other databases and of background groups stay as they are)."""
    old = state()
    with parameters.db.atomic():
        ProjectParameter.delete().execute()
        for n, p in st["project"].items():
            ProjectParameter.create(name=n, amount=p["amount"], formula=p["formula"], data=p["data"])
        Group.get_or_create(name="project")[0].expire()
        for db in set(old["database"]) | set(st["database"]):
            DatabaseParameter.delete().where(DatabaseParameter.database == db).execute()
            for n, p in st["database"].get(db, {}).items():
                DatabaseParameter.create(database=db, name=n, amount=p["amount"], formula=p["formula"], data=p["data"])
            Group.get_or_create(name=db)[0].expire()
        for g in set(old["groups"]) | set(st["groups"]):
            ActivityParameter.delete().where(ActivityParameter.group == g).execute()
            ParameterizedExchange.delete().where(ParameterizedExchange.group == g).execute()
            grp = st["groups"].get(g)
            if grp is None:
                continue
            for n, p in grp["params"].items():
                ActivityParameter.create(group=g, database=grp["database"], code=grp["code"], name=n, amount=p["amount"],
                                         formula=p["formula"], data=p["data"])
            Group.get_or_create(name=g)[0].expire()
    # exchange formulas live in the exchange too (Activity Browser and bw2io read them there)
    for exc_id in set(old["exchanges"]) | set(st["exchanges"]):
        try:
            exc = Exchange(ExchangeDataset.get_by_id(exc_id))
        except ExchangeDataset.DoesNotExist:
            continue
        e = st["exchanges"].get(exc_id)
        if e is None:
            exc._data.pop("formula", None)
            exc._data.pop("original_amount", None)
            if old["exchanges"].get(exc_id, {}).get("amount") is not None:
                exc["amount"] = old["exchanges"][exc_id]["amount"]
        else:
            exc["formula"] = e["formula"]
            if e.get("original_amount") is not None:
                exc["original_amount"] = e["original_amount"]
            elif "original_amount" not in exc._data:
                exc["original_amount"] = exc["amount"]
            ParameterizedExchange.create(exchange=exc_id, group=e["group"], formula=e["formula"])
        exc.save()
    _recalculate()


def _change(new: dict, label: tuple) -> None:
    _evaluate(new)  # raises before anything is written
    before = state()
    _write(new)
    models._changed(label, {"op": "restore_params", "state": _jsonable(before), "now": snapshot()})


def snapshot() -> dict:
    """The managed state as stored in the undo log, to see later whether another program changed it."""
    return json.loads(json.dumps(_jsonable(state()), default=str))


def _project_params_shared() -> bool:
    """Do databases LCA Wrench did not make use parameters? Then project parameters may feed their formulas."""
    mdbs = list(models.model_databases())
    dp, ap = DatabaseParameter.select(), ActivityParameter.select()
    if mdbs:
        dp, ap = dp.where(~(DatabaseParameter.database << mdbs)), ap.where(~(ActivityParameter.database << mdbs))
    return dp.exists() or ap.exists()


def _jsonable(st: dict) -> dict:
    return {**st, "exchanges": {str(k): v for k, v in st["exchanges"].items()}}


def restore(st: dict) -> None:
    """Undo step: back to a saved managed state."""
    st = {**st, "exchanges": {int(k): v for k, v in st["exchanges"].items()}}
    _write(st)


# ---------- the operations the UI calls ----------

def _parse(value: str) -> tuple[float | None, str | None]:
    """'12.5' or '12,5' is an amount, everything else a formula."""
    value = (value or "").strip()
    if not value:
        raise ValueError(_("Bitte einen Wert oder eine Formel eingeben."))
    if _NUMBER.match(value):
        return float(value.replace(",", ".")), None
    return None, value


def _check_name(name: str) -> str:
    name = (name or "").strip()
    if not name.isidentifier() or keyword.iskeyword(name) or name.startswith("__") or name in _BUILTINS:
        raise ValueError(_("«{name}» geht nicht als Name: nur Buchstaben, Ziffern und _, nicht mit einer Ziffer beginnen, "
                           "kein reserviertes Wort (wie «sin» oder «pi»).", name=name))
    return name


def _scope(st: dict, scope: str, database: str | None, activity_id) -> tuple[dict, tuple]:
    """The parameter dict of a scope inside `st` (created if needed) and a label for the undo history."""
    if scope == "project":
        if not models.is_own_copy() and _project_params_shared():
            raise models.ReadOnlyError(_("Datenbanken, die nicht in LCA Wrench angelegt wurden, verwenden Parameter dieses "
                                         "Projekts. Damit dort nichts verloren geht, ändert LCA Wrench Projekt-Parameter "
                                         "nur in einer Kopie des Projekts: oben in der Projektauswahl eine Testkopie anlegen."))
        return st["project"], (_("Projekt"),)
    if database not in st["database"]:
        raise models.ReadOnlyError(_("Parameter gibt es hier nur für eigene Modelle."))
    if scope == "database":
        return st["database"][database], (database,)
    act = bd.get_node(id=int(activity_id))
    models._require_model_node(act)
    g = group_of(act["database"], act["code"])
    grp = st["groups"].setdefault(g, {"database": act["database"], "code": act["code"], "params": {}})
    return grp["params"], (act["name"],)


def set_parameter(scope: str, name: str, value: str, database: str | None = None, activity_id=None,
                  old_name: str | None = None) -> None:
    name = _check_name(name)
    amount, formula = _parse(value)
    st = state()
    params, where = _scope(st, scope, database, activity_id)
    if old_name and old_name != name:
        if name in params:
            raise ValueError(_("Den Namen «{name}» gibt es hier schon.", name=name))
        params[name] = params.pop(old_name)
    p = params.setdefault(name, {"amount": None, "formula": None, "data": {}})
    p["amount"], p["formula"] = (amount if amount is not None else p["amount"]), formula
    if old_name and old_name != name:
        try:
            _evaluate(st)
        except ValueError as e:
            raise ValueError(_("«{name}» wird noch gebraucht: {error}", name=old_name, error=e)) from None
    _change(st, msg("Parameter «{name}» ({where}) = {value}", name=name, where=where[0], value=value.strip()))


def delete_parameter(scope: str, name: str, database: str | None = None, activity_id=None) -> None:
    st = state()
    params, where = _scope(st, scope, database, activity_id)
    if name not in params:
        raise KeyError(_("Den Parameter «{name}» gibt es nicht.", name=name))
    del params[name]
    try:
        _evaluate(st)
    except ValueError as e:
        raise ValueError(_("«{name}» wird noch gebraucht: {error}", name=name, error=e)) from None
    _change(st, msg("Parameter «{name}» ({where}) gelöscht", name=name, where=where[0]))


def set_exchange_formula(exchange_id: int, formula: str | None) -> None:
    """A formula for an amount of an own process; empty removes it (the amount stays as it is)."""
    exc = Exchange(ExchangeDataset.get_by_id(int(exchange_id)))
    act = exc.output
    models._require_model_node(act)
    if exc["type"] == "production":
        raise ValueError(_("Der Referenzfluss bekommt keine Formel."))
    st = state()
    g = group_of(act["database"], act["code"])
    formula = (formula or "").strip() or None
    if formula is None:
        st["exchanges"].pop(int(exchange_id), None)
        label = msg("Formel für «{input}» in «{name}» entfernt", input=exc.input["name"], name=act["name"])
    else:
        if _NUMBER.match(formula):
            raise ValueError(_("Das ist eine Zahl, keine Formel. Zahlen bitte direkt als Menge eingeben."))
        st["groups"].setdefault(g, {"database": act["database"], "code": act["code"],
                                    "params": {f"{DUMMY}{act['code']}__": {"amount": 0, "formula": None, "data": {}}}})
        st["exchanges"][int(exchange_id)] = {"group": g, "formula": formula, "amount": exc["amount"],
                                             "original_amount": exc.get("original_amount", exc["amount"])}
        label = msg("Formel für «{input}» in «{name}»: {formula}", input=exc.input["name"], name=act["name"], formula=formula)
    _change(st, label)


def overview(database: str | None) -> dict:
    """Parameters for the Parameter view: project, the chosen own model and its processes, with current values."""
    st = state()
    try:
        vals, problem = _evaluate(st), None
    except ValueError as e:  # e.g. edited in another program; show the stored values and the problem
        problem = str(e)
        vals = {"project": {n: p["amount"] for n, p in st["project"].items()},
                "database": {db: {n: p["amount"] for n, p in ps.items()} for db, ps in st["database"].items()},
                "groups": {g: {n: p["amount"] for n, p in grp["params"].items()} for g, grp in st["groups"].items()}}

    def rows(params, values):
        return [{"name": n, "amount": values.get(n, p["amount"]), "formula": p["formula"], "comment": p["data"].get("comment", "")}
                for n, p in sorted(params.items(), key=lambda kv: kv[0].lower()) if not n.startswith(DUMMY)]

    out = {"project": rows(st["project"], vals["project"]), "database": None, "processes": [], "problem": problem}
    if database and database in st["database"]:
        out["database"] = {"name": database, "params": rows(st["database"][database], vals["database"][database])}
        n_formulas = {}
        for e in st["exchanges"].values():
            n_formulas[e["group"]] = n_formulas.get(e["group"], 0) + 1
        for p in models.list_processes(database):
            act = bd.get_node(id=int(p["id"]))
            g = group_of(act["database"], act["code"])
            grp = st["groups"].get(g, {"params": {}})
            out["processes"].append({**p, "params": rows(grp["params"], vals["groups"].get(g, {})), "formulas": n_formulas.get(g, 0)})
    return out


def drop_unused_project_parameters(names) -> None:
    """Remove these project parameters where no formula needs them any more (undo of an import), without a journal entry."""
    st = state()
    changed = False
    for n in names:
        if n in st["project"]:
            trial = {**st, "project": {k: v for k, v in st["project"].items() if k != n}}
            try:
                _evaluate(trial)
            except ValueError:
                continue
            st, changed = trial, True
    if changed:
        _write(st)


def forget_database(database: str, codes) -> None:
    """After an own model was deleted: its parameter groups go too (Brightway leaves the groups behind)."""
    names = [database] + [group_of(database, c) for c in codes]
    with parameters.db.atomic():
        DatabaseParameter.delete().where(DatabaseParameter.database == database).execute()
        ActivityParameter.delete().where(ActivityParameter.database == database).execute()
        ParameterizedExchange.delete().where(ParameterizedExchange.group << names).execute()
        GroupDependency.delete().where((GroupDependency.group << names) | (GroupDependency.depends << names)).execute()
        Group.delete().where(Group.name << names).execute()


def reattach(key) -> None:
    """After an undo recreated a process or exchange: register its exchange formulas in its group again."""
    act = bd.get_node(database=key[0], code=key[1])
    g = group_of(act["database"], act["code"])
    if any("formula" in e for e in act.exchanges()) and Group.select().where(Group.name == g).exists():
        parameters.add_exchanges_to_group(g, act)
        _recalculate()


def restore_ids(st: dict, moved: dict) -> dict:
    """A saved state whose exchanges were recreated by an undo (new ids): point it at the new ids."""
    ex = {}
    for k, v in st["exchanges"].items():
        ex[str(moved.get(int(k), int(k)))] = v
    return {**st, "exchanges": ex}
