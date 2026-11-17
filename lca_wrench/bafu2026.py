"""BAFU:2026 with the EF 3.1 methods, imported with sentier-brightway into a project of its own.

sentier-brightway (https://github.com/sentier-dev/sentier-brightway) downloads the BAFU-2026 v1 inventory, the EF 3.1
biosphere and the 25 EF 3.1 methods from pinned commits of the Sentier data repositories (each file checked against
its sha256, about 36 MB, cached in the user cache folder) and writes them with bw2data:

- `bafu-2026`: 11'947 processes (background data)
- `ef-3.1-biosphere`: EF 3.1 elementary flows, with the BAFU emissions relinked onto them
- `bafu-2026-residual`: the BAFU flows without an EF 3.1 counterpart (kept, no factor)
- methods `("sentier", "EF v3.1", <category>)`

The import runs as a job of `imports.py`, which picks the target (a new or an empty project) and removes what a failed
import made. Other projects are not touched.
"""

from __future__ import annotations

import logging
import time

from .i18n import _

log = logging.getLogger("lca_wrench")

PROJECT = "bafu-2026"
METHOD_FAMILY = "sentier"


def available() -> bool:
    """Is sentier-brightway installed in this Python?"""
    try:
        import sentier_brightway  # noqa: F401
    except ImportError:
        return False
    return True


def install(project: str | None = None) -> dict:
    """Write BAFU:2026 and EF 3.1 into `project` (default `PROJECT`; created if missing) and leave it current. Returns
    the linking coverage as reported by sentier-brightway. Refuses a project that already has any of its databases."""
    project = project or PROJECT
    if not available():
        raise ValueError(_("Für den Import von BAFU 2026 fehlt das Paket sentier-brightway. Installiere LCA Wrench "
                           "neu (Installationsskript), dann ist es dabei."))
    import sentier_brightway as sb
    from sentier_brightway.constants import citation
    from sentier_brightway.fetch import FetchError
    from sentier_brightway.writer import ExistingDatabaseError

    start = time.time()
    try:
        cov = sb.import_db(project)
    except ExistingDatabaseError as e:
        raise ValueError(_("Das Projekt «{name}» hat schon Daten von BAFU 2026.", name=project)) from e
    except FetchError as e:
        raise ValueError(_("Die Daten für BAFU 2026 liessen sich nicht laden (github.com). Internetverbindung "
                           "prüfen und nochmals versuchen. Details: {error}", error=e)) from e
    except Exception as e:
        raise ValueError(_("Der Import von BAFU 2026 ist fehlgeschlagen: {error}", error=e)) from e
    log.info("BAFU 2026 imported into %s (%.0f s)", project, time.time() - start)
    return {
        "project": project,
        "processes": cov.processes,
        "methods": cov.methods,
        "flows_used": cov.flows_used,
        "flows_mapped": cov.flows_mapped,
        "exchange_rows": cov.exchange_rows,
        "exchange_rows_mapped": cov.exchange_rows_mapped,
        "seconds": round(time.time() - start, 1),
        "citation": citation(cov.source),
    }
