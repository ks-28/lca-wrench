"""Changes from outside: another process edits the project, the service notices and recalculates."""

import subprocess
import sys
import time

import bw2calc as bc
import bw2data as bd
import pytest

from conftest import TEST_PROJECT
from lca_wrench import models, service as s

EXT_EDIT = """
import sys, warnings
warnings.filterwarnings("ignore")
import bw2data as bd
bd.projects.set_current(sys.argv[1])
from bw2data.backends.schema import ExchangeDataset as ED
from bw2data.backends.proxies import Exchange
e = Exchange(ED.get_by_id(int(sys.argv[2])))
e["amount"] = float(sys.argv[3])
e.save()
"""

EXT_NEW_BG = """
import sys, warnings
warnings.filterwarnings("ignore")
import bw2data as bd
bd.projects.set_current(sys.argv[1])
db = bd.Database(sys.argv[2])
db.write({(sys.argv[2], "a"): {"name": "a", "unit": "kg", "location": "CH", "type": "process",
          "exchanges": [{"input": (sys.argv[2], "a"), "amount": 1, "type": "production"}]}})
"""


def outside(code, *args):
    r = subprocess.run([sys.executable, "-c", code, TEST_PROJECT, *map(str, args)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]


@pytest.fixture()
def model():
    bd.projects.set_current(TEST_PROJECT)
    s.acknowledge()
    models.create_database("zz-Extern")
    hit = [h for h in s.search("electricity low voltage", "CH") if h["unit"] == "kWh"][0]
    pid = models.create_process("zz-Extern", "Strom-Test", "kilowatt hour", "CH")
    eid = models.add_exchange(pid, hit["id"], 3.0)
    s.acknowledge()
    yield int(pid), int(eid), int(hit["id"])
    bd.projects.set_current(TEST_PROJECT)
    s.sync_external()
    if "zz-Extern" in bd.databases:
        models.delete_database("zz-Extern")
    for name in ("zz-Extern-bg",):
        if name in bd.databases:
            del bd.databases[name]
    s.acknowledge()


def bw2calc_score(node_id, method):
    lca = bc.LCA({node_id: 1.0}, method)
    lca.lci()
    lca.lcia()
    return lca.score


def test_no_change_no_reload(model):
    n = s.EXTERNAL["count"]
    assert s.sync_external() is False
    # our own edits are not "outside" changes
    models.update_exchange(model[1], amount=4.0)
    s.acknowledge()
    assert s.sync_external() is False and s.EXTERNAL["count"] == n


def test_outside_edit_is_noticed_and_recalculated(model):
    pid, eid, _ = model
    method = s.CLIMATE_METHOD
    before = models.system().score({pid: 1.0}, method)
    assert before == pytest.approx(bw2calc_score(pid, method), rel=1e-8)
    n = s.EXTERNAL["count"]
    bg_before = models.system().bg
    time.sleep(0.05)
    outside(EXT_EDIT, eid, 6.0)
    assert s.sync_external() is True
    assert s.EXTERNAL["count"] == n + 1 and "zz-Extern" in s.EXTERNAL["what"]
    after = models.system().score({pid: 1.0}, method)
    assert after == pytest.approx(2 * before, rel=1e-8)  # amount 3 -> 6
    assert after == pytest.approx(bw2calc_score(pid, method), rel=1e-8)
    assert models.system().bg is bg_before  # only a model changed: the slow background rebuild is skipped
    s.acknowledge()
    assert s.sync_external() is False


def test_outside_change_clears_undo_steps(model):
    pid, eid, _ = model
    assert models.journal_length() > 0
    outside(EXT_EDIT, eid, 5.0)
    assert s.sync_external() is True
    assert models.journal_length() == 0


def test_new_background_database_rebuilds_background(model):
    bg_before = models.system().bg
    outside(EXT_NEW_BG, "zz-Extern-bg")
    assert s.sync_external() is True
    assert "zz-Extern-bg" in s.EXTERNAL["what"]
    assert models.system().bg is not bg_before
    assert "zz-Extern-bg" in {d["name"] for d in s.state()["databases"]}
