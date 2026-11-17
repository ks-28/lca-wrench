"""Test setup: all tests run in the Brightway project `lca-wrench-test`.

The project is a copy of `bafu-2025` (background data only, no own models),
created once. The real working project `bafu-2025` and the real registry
file `lca-wrench.json` are never touched by tests: set_current() refuses
`bafu-2025` and the registry points to a temporary file.
"""

import os
import tempfile
from pathlib import Path

import bw2data as bd
import pytest

TEST_PROJECT = "lca-wrench-test"
SOURCE_PROJECT = "bafu-2025"
BACKGROUND_DBS = {"BAFU-2025-v2", "BAFU-2025-biosphere"}

_registry_dir = tempfile.mkdtemp(prefix="lca-wrench-test-registry-")
os.environ["LCA_WRENCH_REGISTRY"] = str(Path(_registry_dir) / "lca-wrench.json")
# the tests were written against the German texts (the keys); English is the default for users (test_i18n checks it)
os.environ["LCA_WRENCH_LANG"] = "de"

_orig_set_current = type(bd.projects).set_current


def _guarded_set_current(self, project_name, *args, **kwargs):
    if project_name == SOURCE_PROJECT:
        raise RuntimeError(f"Tests must not open the project “{SOURCE_PROJECT}”.")
    result = _orig_set_current(self, project_name, *args, **kwargs)
    # tests switch projects directly; the app counts a project as open only once the user chose it
    from lca_wrench import service

    service.OPEN["project"] = project_name
    return result


def pytest_configure(config):
    type(bd.projects).set_current = _guarded_set_current


def _ensure_test_project() -> bool:
    """Create the test project from the source project if missing; strip foreign databases."""
    if TEST_PROJECT not in bd.projects:
        if SOURCE_PROJECT not in bd.projects:
            return False
        # copy_project works on the current project; the source is only read.
        type(bd.projects).set_current = _orig_set_current
        try:
            bd.projects.set_current(SOURCE_PROJECT)
            bd.projects.copy_project(TEST_PROJECT, switch=True)
        finally:
            type(bd.projects).set_current = _guarded_set_current
    bd.projects.set_current(TEST_PROJECT)
    for name in list(bd.databases):
        if name not in BACKGROUND_DBS:
            del bd.databases[name]
    # parameters of earlier runs (Brightway keeps the groups of deleted databases)
    from bw2data.parameters import Group, GroupDependency, ProjectParameter

    ProjectParameter.delete().execute()
    stale = [g.name for g in Group.select() if g.name != "project" and g.name.split(":")[0] not in bd.databases]
    GroupDependency.delete().where((GroupDependency.group << stale) | (GroupDependency.depends << stale)).execute()
    Group.delete().where(Group.name << stale).execute()
    return BACKGROUND_DBS <= set(bd.databases)


# Tests that need no Brightway data at all: they run on a fresh clone, before setup_daten.py.
NO_DATA = {"test_lock.py", "test_i18n.py::test_every_server_text_has_english",
           "test_i18n.py::test_every_ui_text_has_english", "test_i18n.py::test_rendered_later_in_the_readers_language"}


def _needs_data(item) -> bool:
    name = Path(str(item.fspath)).name
    return name not in NO_DATA and f"{name}::{item.originalname or item.name}" not in NO_DATA


_HAVE_DATA: bool | None = None


def pytest_collection_modifyitems(config, items):
    """Without the BAFU data, skip the tests that need it (before any of their fixtures runs); the others still run."""
    global _HAVE_DATA
    if not any(_needs_data(i) for i in items):
        return
    _HAVE_DATA = _ensure_test_project()
    if _HAVE_DATA:
        # Most tests compare with plain bw2calc on the methods as stored, so the completed factors (completion.py, on
        # by default for users) are off here; tests/test_completion.py switches them on and checks both.
        from lca_wrench import completion

        completion.set_enabled(False)
        return
    skip = pytest.mark.skip(reason=f"the Brightway project {SOURCE_PROJECT} is missing: run setup_daten.py first")
    for item in items:
        if _needs_data(item):
            item.add_marker(skip)


@pytest.fixture(scope="session", autouse=True)
def test_project():
    yield TEST_PROJECT if _HAVE_DATA else None
