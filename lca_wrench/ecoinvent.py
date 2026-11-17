"""ecoinvent into a project, the way the Activity Browser 3 does it: bw2io `import_ecoinvent_release`.

Two ways in, both through the same bw2io function, so linking, biosphere and methods are identical:

- **ecoinvent account:** ecoinvent_interface logs in with the user's own ecoinvent login, downloads the release
  (about 1 GB, kept in its cache for the next time) and the LCIA implementation file.
- **Local file:** the ecoSpold02 archive downloaded from ecoinvent.org (`ecoinvent 3.10_cutoff_ecoSpold02.7z`, or the
  unpacked folder) and, for the methods, the LCIA file (`ecoinvent 3.10_LCIA_implementation.7z` or the `.xlsx` in it).
  bw2io then gets a stand-in for ecoinvent_interface that hands it these files instead of downloading them.

Result: databases `ecoinvent-<version>-biosphere` and `ecoinvent-<version>-<system model>`, methods
`("ecoinvent-<version>", …)`. The login is passed on to ecoinvent only; it is stored on this computer only when asked
for (`remember`, in ecoinvent_interface's own place, which the Activity Browser uses as well), never logged.
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

from .i18n import _, msg

SYSTEM_MODELS = ("cutoff", "apos", "consequential", "EN15804")
# names of the local files: "ecoinvent 3.10_cutoff_ecoSpold02.7z", "ecoinvent 3.9.1_apos_ecoSpold02"
FILENAME = re.compile(r"(\d+\.\d+(?:\.\d+)?)[ _-]+(cutoff|cut-off|apos|consequential|conseq|en15804)", re.I)
_SM_ALIASES = {"cut-off": "cutoff", "conseq": "consequential", "en15804": "EN15804"}

Phase = Callable[[tuple], None]


def available() -> bool:
    try:
        import ecoinvent_interface  # noqa: F401
    except ImportError:
        return False
    return True


def saved_login() -> str | None:
    """The ecoinvent user name stored on this computer (by the Activity Browser or an earlier import), if any."""
    if not available():
        return None
    import ecoinvent_interface as ei

    s = ei.Settings()
    return s.username if s.username and s.password else None


def guess_from_filename(path: str) -> dict:
    m = FILENAME.search(Path(path).name)
    if not m:
        return {}
    sm = m.group(2).lower()
    return {"version": m.group(1), "system_model": _SM_ALIASES.get(sm, sm)}


def _settings(username: str | None, password: str | None):
    import ecoinvent_interface as ei

    if username and password:
        return ei.Settings(username=username, password=password)
    s = ei.Settings()
    if not (s.username and s.password):
        raise ValueError(_("Bitte Benutzername und Passwort von ecoinvent angeben."))
    return s


def versions(username: str | None, password: str | None) -> list[str]:
    """Log in and list the releases this ecoinvent account may download, newest first."""
    import ecoinvent_interface as ei
    import requests

    try:
        found = ei.EcoinventRelease(_settings(username, password)).list_versions()
    except requests.HTTPError as e:
        raise ValueError(_("Anmeldung bei ecoinvent fehlgeschlagen. Benutzername und Passwort prüfen.")) from e
    except requests.RequestException as e:
        raise ValueError(_("ecoinvent ist nicht erreichbar. Internetverbindung prüfen.")) from e

    def key(v):
        return tuple(int(x) if x.isdigit() else 0 for x in v.split("."))

    return sorted(set(found), key=key, reverse=True)


def check(version: str, system_model: str) -> None:
    if not re.fullmatch(r"3\.\d+(\.\d+)?", version or ""):
        raise ValueError(_("Unbekannte ecoinvent-Version «{v}» (erwartet z.B. 3.10).", v=version))
    if system_model not in SYSTEM_MODELS:
        raise ValueError(_("Unbekanntes Systemmodell «{m}».", m=system_model))


def database_name(version: str, system_model: str) -> str:
    return f"ecoinvent-{version}-{system_model}"


# ---------- the import itself ----------

def _with_steps(ei_like, phase: Phase, local: bool):
    """ecoinvent_interface (or the local stand-in) as bw2io sees it, reporting each step to `phase`."""

    class Release:
        def __init__(self, inner):
            self.inner = inner

        def list_versions(self):
            return self.inner.list_versions()

        def list_system_models(self, version, *a, **k):
            return self.inner.list_system_models(version, *a, **k)

        def get_release(self, **k):
            if not local:  # local files are unpacked before bw2io starts
                phase(msg("ecoinvent herunterladen (beim ersten Mal ca. 1 GB, danach aus dem Zwischenspeicher) …"))
            return self.inner.get_release(**k)

    class Module:
        ReleaseType = ei_like.ReleaseType

        @staticmethod
        def Settings(**k):  # noqa: N802 - the name bw2io calls
            return ei_like.Settings(**k)

        @staticmethod
        def EcoinventRelease(settings):  # noqa: N802
            if not local:
                phase(msg("Bei ecoinvent anmelden …"))
            return Release(ei_like.EcoinventRelease(settings))

        @staticmethod
        def get_excel_lcia_file_for_version(release, version):
            phase(msg("Wirkungsmethoden laden und zuordnen …"))
            return ei_like.get_excel_lcia_file_for_version(release=release.inner, version=version)

    return Module


def _use_mp() -> bool:
    """bw2io reads the datasets with a process pool. Its workers (spawn) import the main module again; when that
    cannot be done (a script from stdin, some embedded Pythons) they fail and are restarted without end."""
    main = sys.modules.get("__main__")
    return bool(getattr(main, "__file__", None) or getattr(getattr(main, "__spec__", None), "name", None))


def _run(version: str, system_model: str, ei_like, phase: Phase, *, local: bool, lcia: bool,
         username: str | None = None, password: str | None = None, use_mp: bool | None = None) -> None:
    import bw2io.ecoinvent as bie

    base = bie.SingleOutputEcospold2Importer

    class Importer(base):  # same importer, with the two long steps shown
        def __init__(self, *a, **k):
            phase(msg("Datensätze lesen und verknüpfen (mehrere Minuten) …"))
            super().__init__(*a, **k)

        def write_database(self, *a, **k):
            phase(msg("Datenbank schreiben (mehrere Minuten) …"))
            return super().write_database(*a, **k)

    saved = bie.ei, bie.SingleOutputEcospold2Importer
    bie.ei, bie.SingleOutputEcospold2Importer = _with_steps(ei_like, phase, local), Importer
    try:
        bie.import_ecoinvent_release(version=version, system_model=system_model, username=username,
                                     password=password, lcia=lcia, use_mp=_use_mp() if use_mp is None else use_mp)
    finally:
        bie.ei, bie.SingleOutputEcospold2Importer = saved


def install_remote(version: str, system_model: str, username: str | None, password: str | None, remember: bool,
                   phase: Phase, lcia: bool | None = None) -> dict:
    """Into the current project, with the user's ecoinvent login."""
    import ecoinvent_interface as ei
    import requests

    check(version, system_model)
    settings = _settings(username, password)
    try:
        _run(version, system_model, ei, phase, local=False, lcia=int(version.split(".")[1]) >= 4 if lcia is None else lcia,
             username=settings.username, password=settings.password)
    except requests.HTTPError as e:
        raise ValueError(_("Anmeldung oder Download bei ecoinvent fehlgeschlagen: {error}", error=e)) from e
    except requests.RequestException as e:
        raise ValueError(_("ecoinvent ist nicht erreichbar. Internetverbindung prüfen.")) from e
    if remember and username and password:
        ei.permanent_setting("username", username)
        ei.permanent_setting("password", password)
    return {"database": database_name(version, system_model)}


class _LocalRelease:
    """The part of ecoinvent_interface that bw2io uses, answered from local files instead of the ecoinvent server."""

    def __init__(self, version: str, system_model: str, lci_dir: Path, lcia_file: Path | None):
        import ecoinvent_interface as ei

        self.ReleaseType = ei.ReleaseType
        self.version, self.system_model, self.lci_dir, self.lcia_file = version, system_model, lci_dir, lcia_file

    def Settings(self, **k):  # noqa: N802
        return SimpleNamespace(username="local", password="local")

    def EcoinventRelease(self, settings):  # noqa: N802
        return self

    def list_versions(self):
        return [self.version]

    def list_system_models(self, version, *a, **k):
        return [self.system_model]

    def get_release(self, **k):
        return self.lci_dir

    def get_excel_lcia_file_for_version(self, release, version):
        return self.lcia_file


def _unpack(path: Path, into: Path) -> Path:
    import py7zr

    if path.suffix.lower() == ".7z":
        with py7zr.SevenZipFile(path, "r") as archive:
            archive.extractall(into)
    elif path.suffix.lower() == ".zip":
        shutil.unpack_archive(path, into)
    else:
        raise ValueError(_("Unbekanntes Dateiformat: {name} (erwartet .7z, .zip oder einen Ordner).", name=path.name))
    return into


def _release_dir(root: Path) -> Path:
    """The folder holding `datasets` and `MasterData` (directly in the archive or one level down)."""
    for d in [root, *sorted(p for p in root.iterdir() if p.is_dir())]:
        if (d / "datasets").is_dir() and (d / "MasterData" / "ElementaryExchanges.xml").is_file():
            return d
    raise ValueError(_("In «{name}» fehlen die Ordner datasets und MasterData. Gebraucht wird die Datei "
                       "ecoSpold02 von ecoinvent.org (z.B. «ecoinvent 3.10_cutoff_ecoSpold02.7z»).", name=root.name))


def _lcia_xlsx(path: Path, into: Path) -> Path:
    if path.suffix.lower() == ".xlsx":
        return path
    files = [p for p in _unpack(path, into).rglob("*.xlsx") if "lcia" in p.name.lower()]
    if not files:
        raise ValueError(_("In «{name}» ist keine LCIA-Datei (.xlsx).", name=path.name))
    return sorted(files, key=lambda p: len(p.name))[0]


def install_local(version: str, system_model: str, lci_path: str, lcia_path: str | None, phase: Phase) -> dict:
    """Into the current project, from the files downloaded from ecoinvent.org. Unpacks into a temporary folder that
    is removed afterwards; an unpacked folder given by the user is only read."""
    check(version, system_model)
    lci = Path(lci_path).expanduser()
    if not lci.exists():
        raise ValueError(_("Datei oder Ordner nicht gefunden: {path}", path=lci))
    lcia = Path(lcia_path).expanduser() if lcia_path else None
    if lcia and not lcia.is_file():
        raise ValueError(_("Datei nicht gefunden: {path}", path=lcia))
    tmp = Path(tempfile.mkdtemp(prefix="lca-wrench-ecoinvent-"))
    try:
        if lci.is_dir():
            lci_dir = _release_dir(lci)
        else:
            phase(msg("ecoinvent-Daten auspacken …"))
            lci_dir = _release_dir(_unpack(lci, tmp / "lci"))
        lcia_file = _lcia_xlsx(lcia, tmp / "lcia") if lcia else None
        many = sum(1 for _ in (lci_dir / "datasets").glob("*.spold")) > 200
        _run(version, system_model, _LocalRelease(version, system_model, lci_dir, lcia_file), phase,
             local=True, lcia=lcia_file is not None, use_mp=many and _use_mp())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {"database": database_name(version, system_model)}
