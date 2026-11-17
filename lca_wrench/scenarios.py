"""Future scenarios of ecoinvent with premise (https://github.com/polca/premise), as new background databases.

premise takes an ecoinvent database of the project (3.5 to 3.12, cut-off or consequential) and changes it along a
scenario of an integrated assessment model (IAM: REMIND, IMAGE, MESSAGE, …; pathways such as SSP2-NPi or
SSP2-PkBudg1000) for a year: power plant efficiencies and electricity mixes, steel, cement, fuels, transport and
more. Each scenario and year becomes a database of its own, e.g. "ecoinvent-3.10-cutoff remind SSP2-NPi 2040". With
the background choice (backgrounds.py) the same model is then calculated on today's data or on the scenario.

premise needs older numpy, pandas and scipy than LCA Wrench, so it gets an environment of its own next to the app's
(`.premise-venv`, set up once with uv from `premise-requirements.txt`, with the same Brightway versions as the app,
about 1 GB) and runs there as a separate process (premise_worker.py). The app stays usable meanwhile. The IAM data
of premise are encrypted; the key is free and comes from the premise authors (see their README). It is passed to
the worker only, and kept on this computer only when asked for.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import bw2data as bd

from .i18n import _

HERE = Path(__file__).resolve().parent
APP_DIR = Path(sys.prefix).resolve().parent  # the folder holding .venv (the installed app, or the repository)
ENV_DIR = APP_DIR / ".premise-venv"
REQUIREMENTS = HERE / "premise-requirements.txt"
WORKER = HERE / "premise_worker.py"
SOURCE = re.compile(r"ecoinvent[-_ ](3\.\d+(?:\.\d+)?)[-_ ](cutoff|consequential)", re.I)
_constants: dict = {}


def env_python() -> Path:
    """The Python of the premise environment (LCA_WRENCH_PREMISE_PYTHON for tests)."""
    if os.environ.get("LCA_WRENCH_PREMISE_PYTHON"):
        return Path(os.environ["LCA_WRENCH_PREMISE_PYTHON"])
    return ENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def uv() -> str | None:
    for p in (APP_DIR / ".tools" / ("uv.exe" if os.name == "nt" else "uv"),):
        if p.is_file():
            return str(p)
    return shutil.which("uv")


def _env() -> dict:
    env = dict(os.environ)
    extra = os.environ.get("LCA_WRENCH_PREMISE_PATH")
    if extra:
        env["PYTHONPATH"] = extra + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONWARNINGS"] = "ignore"
    return env


# Run in the premise environment. Besides what premise lists as supported: the record of its Zenodo archive of IAM
# scenarios, the file premise would download there for each model and pathway (its own naming rule, e.g. IMAGE with
# underscores), and the scenario files already on this computer. premise lists every pathway for every model, but
# the archive has only some pairs (premise 2.5.2: no "SSP2-Base" at all), and asking for another fails with a 404.
_CONSTANTS_CODE = r"""
import json, os, premise
from premise.utils import load_constants
c = load_constants()
out = {'version': '.'.join(map(str, premise.__version__)), 'ei_versions': c.get('SUPPORTED_EI_VERSIONS'),
       'models': c.get('SUPPORTED_MODELS'),
       'pathways': [p for p in c.get('SUPPORTED_PATHWAYS', []) if p not in c.get('UNAVAILABLE_PATHWAYS', [])],
       'record': None, 'files': {}, 'local': {}}
try:
    from premise.scenario_downloader import ZENODO_IAM_SCENARIO_RECORD_ID, get_scenario_url
    out['record'] = str(ZENODO_IAM_SCENARIO_RECORD_ID)
    out['files'] = {m: {p: get_scenario_url(m, p).rsplit('/', 1)[-1] for p in out['pathways']} for m in out['models']}
except Exception:
    pass
try:
    from premise.filesystem_constants import IAM_OUTPUT_DIR
    have = set(os.listdir(IAM_OUTPUT_DIR))
    try:
        from premise.scenario_downloader import get_scenario_file_stems as stems
    except Exception:
        stems = lambda m, p: (m + '_' + p,)
    out['local'] = {m: [p for p in out['pathways']
                        if any(s + e in have for s in stems(m, p) for e in ('.csv', '.mif', '.xls', '.xlsx'))]
                    for m in out['models']}
except Exception:
    pass
print('@@' + json.dumps(out))
"""
ZENODO_RECORD_API = "https://zenodo.org/api/records/{record}"
_archive: dict = {}  # record -> (time, file names in it, or None when it could not be read)


def constants() -> dict | None:
    """What this premise supports (ecoinvent versions, IAM models, pathways), or None when it is not set up."""
    py = env_python()
    if not py.is_file():
        return None
    if str(py) not in _constants:
        try:
            # premise writes logs into the folder it starts in: a temporary one, not the app's
            with tempfile.TemporaryDirectory(prefix="lca-wrench-premise-") as tmp:
                out = subprocess.run([str(py), "-c", _CONSTANTS_CODE], capture_output=True, text=True, timeout=300,
                                     env=_env(), cwd=tmp).stdout
            line = next(x for x in out.splitlines() if x.startswith("@@"))
            _constants[str(py)] = json.loads(line[2:])
        except (OSError, StopIteration, ValueError, subprocess.TimeoutExpired):
            return None
    return _constants[str(py)]


def archive_files(record: str) -> set[str] | None:
    """The file names in premise's Zenodo archive of IAM scenarios, None when it cannot be reached (kept for the
    session; a failure is tried again after ten minutes)."""
    if not record.isdigit():
        return None
    hit = _archive.get(record)
    if hit and (hit[1] is not None or time.time() - hit[0] < 600):
        return hit[1]
    try:
        import requests

        r = requests.get(ZENODO_RECORD_API.format(record=record), timeout=10,
                         headers={"Accept": "application/json", "User-Agent": "LCA-Wrench"})
        r.raise_for_status()
        files = {f["key"] for f in r.json().get("files") or []}
    except Exception:  # noqa: BLE001 - offline, Zenodo down or another answer: fall back to premise's own list
        files = None
    _archive[record] = (time.time(), files)
    return files


def offered(c: dict | None) -> dict[str, list[str]] | None:
    """For each IAM model the pathways premise can really use: its scenario file is in the Zenodo archive or already
    on this computer. None when that cannot be told (archive not reachable, or an older premise): then every model
    and pathway premise lists is offered."""
    if not c or not c.get("record") or not c.get("files"):
        return None
    have = archive_files(c["record"])
    if have is None:
        return None
    local = c.get("local") or {}
    out = {}
    for m in c.get("models") or []:
        ps = [p for p in c.get("pathways") or [] if (c["files"].get(m) or {}).get(p) in have or p in (local.get(m) or [])]
        if ps:
            out[m] = ps
    return out


def explain(error: str) -> str:
    """premise's error for a scenario file the archive does not have (HTTP 404 at zenodo.org), in plain words."""
    m = re.search(r"404 Client Error.*?zenodo\.org/\S*/files/(\S+)", error or "")
    if not m:
        return error
    return _("Die Szenariodatei {f} gibt es im Archiv von premise bei Zenodo nicht. Bitte ein anderes Modell oder "
             "einen anderen Pfad wählen.", f=m.group(1))


def setup_command() -> list[list[str]]:
    """The commands that set up the premise environment (uv: a venv with this Python, then the packages)."""
    tool = uv()
    if not tool:
        raise ValueError(_("Für premise fehlt das Installationswerkzeug uv. Installiere LCA Wrench neu "
                           "(Installationsskript), dann ist es dabei."))
    return [[tool, "venv", "--allow-existing", "--python", sys.executable, str(ENV_DIR)],
            [tool, "pip", "install", "--python", str(ENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")),
             "-r", str(REQUIREMENTS)]]


def forget_constants() -> None:
    _constants.clear()


# ---------- the run ----------

def sources(roles: dict) -> list[dict]:
    """ecoinvent databases of the project premise can start from, with version and system model."""
    out = []
    for name, r in sorted(roles.items()):
        m = SOURCE.search(name)
        if r == "background" and m and not (bd.databases.get(name) or {}).get("lca_wrench"):
            out.append({"name": name, "version": m.group(1), "system_model": m.group(2).lower()})
    return out


def biosphere_of(name: str) -> str:
    deps = [d for d in (bd.databases.get(name) or {}).get("depends") or () if d != name]
    return deps[0] if deps else "biosphere3"


def scenario_name(source: str, model: str, pathway: str, year: int) -> str:
    return f"{source} {model} {pathway} {year}"


def plan(opts: dict, roles: dict) -> dict:
    """Check a request and turn it into the worker's task. Raises ValueError with a message for the user."""
    src = next((s for s in sources(roles) if s["name"] == opts.get("source_db")), None)
    if src is None:
        raise ValueError(_("Bitte eine ecoinvent-Datenbank des Projekts als Ausgangspunkt wählen."))
    c = constants()
    if c is None:
        raise ValueError(_("premise ist noch nicht eingerichtet."))
    if src["version"] not in (c.get("ei_versions") or []):
        raise ValueError(_("premise {v} kann ecoinvent {ei} nicht verarbeiten (nur {ok}).", v=c.get("version"),
                           ei=src["version"], ok=", ".join(c.get("ei_versions") or [])))
    model = (opts.get("model") or "").lower()
    if model not in (c.get("models") or []):
        raise ValueError(_("Unbekanntes Modell «{m}».", m=model))
    pathway = opts.get("pathway") or ""
    if pathway not in (c.get("pathways") or []):
        raise ValueError(_("Unbekannter Pfad «{p}».", p=pathway))
    av = offered(c)
    if av is not None and pathway not in av.get(model, []):
        raise ValueError(_("Für {m} gibt es den Pfad «{p}» im Archiv von premise {v} nicht. Vorhanden: {list}.", m=model,
                           p=pathway, v=c.get("version"), list=", ".join(av.get(model, [])) or "–"))
    years = sorted({int(y) for y in opts.get("years") or []})
    if not years or any(not 2005 <= y <= 2100 for y in years):
        raise ValueError(_("Bitte ein oder mehrere Jahre zwischen 2005 und 2100 angeben."))
    key = (opts.get("key") or "").strip() or saved_key()
    if not key:
        raise ValueError(_("Bitte den Schlüssel für die Szenariodaten von premise angeben."))
    names = [scenario_name(src["name"], model, pathway, y) for y in years]
    taken = [n for n in names if n in bd.databases]
    if taken:
        raise ValueError(_("Eine Datenbank «{name}» gibt es schon.", name=taken[0]))
    return {"project": bd.projects.current, "source_db": src["name"], "source_version": src["version"],
            "system_model": src["system_model"], "biosphere": biosphere_of(src["name"]), "key": key,
            "scenarios": [{"model": model, "pathway": pathway, "year": y} for y in years], "names": names}


# the key, kept on this computer only when asked for (next to LCA Wrench's registry, not in any project)

def _key_file() -> Path:
    from . import registry

    return Path(registry.path()).with_name("premise-key.txt")


def saved_key() -> str | None:
    try:
        return _key_file().read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def remember_key(key: str) -> None:
    f = _key_file()
    f.write_text(key.strip(), encoding="utf-8")
    try:
        f.chmod(0o600)
    except OSError:
        pass
