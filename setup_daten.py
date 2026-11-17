"""One-time data setup for the LCA Wrench demo project.

- Installs the free BAFU:2025 template project from files.brightway.dev
  (official Brightway template source, ~62 MB) if it is missing.
- Adds two methods derived from Ecological Scarcity 2021 (UBP):
  * Klimawandel in kg CO2-eq: the UBP global-warming factors divided by the
    eco-factor of CO2 (1000 UBP per kg), which yields the GWP values used there.
  * UBP gesamt: sum of all 21 UBP categories per flow.

With --bafu-2026 it also imports BAFU:2026 with the 25 EF 3.1 methods into the new project bafu-2026
(sentier-brightway, lca_wrench/bafu2026.py); an existing bafu-2026 is left as it is.

Only touches the projects named here, never other projects.
"""

import sys

import bw2data as bd
from bw2io import remote

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from lca_wrench import bafu2026  # noqa: E402
from lca_wrench.service import CLIMATE_METHOD, PROFILE_FAMILY, UBP_TOTAL_METHOD  # noqa: E402

PROJECT = "bafu-2025"
TEMPLATE = "BAFU-2025-v2"


def main() -> None:
    if PROJECT not in bd.projects:
        print(f"Downloading the template {TEMPLATE} (about 62 MB) ...")
        remote.install_project(TEMPLATE, PROJECT)
    bd.projects.set_current(PROJECT)

    family = sorted(m for m in bd.methods if m[0] == PROFILE_FAMILY)
    if not family:
        sys.exit(f"Method family {PROFILE_FAMILY} is missing in project {PROJECT}.")

    gw = bd.Method((PROFILE_FAMILY, "Global warming")).load()
    co2 = [cf for key, cf in gw if bd.get_node(id=key)["name"] == "Carbon dioxide, fossil"
           and tuple(bd.get_node(id=key)["categories"]) == ("emissions to air",)]
    if co2 != [1000.0]:
        sys.exit(f"Unexpected UBP factor for CO2: {co2}. Derivation stopped.")
    m = bd.Method(CLIMATE_METHOD)
    m.register(unit="kg CO2-eq", description="Global warming potential derived from the Ecological Scarcity "
                                              "method 2021: UBP factor divided by 1000 UBP per kg CO2.")
    m.write([(key, cf / 1000.0) for key, cf in gw])

    total: dict = {}
    for mt in family:
        for key, cf in bd.Method(mt).load():
            total[key] = total.get(key, 0.0) + cf
    t = bd.Method(UBP_TOTAL_METHOD)
    t.register(unit="Pt", description="Sum of all 21 categories of Ecological Scarcity 2021.")
    t.write(list(total.items()))
    print(f"Done: project {PROJECT}, {len(gw)} climate factors, {len(total)} UBP factors in total.")


def main_2026() -> None:
    if bafu2026.PROJECT in bd.projects:
        print(f"Project {bafu2026.PROJECT} already exists, nothing changed.")
        return
    print("Importing BAFU 2026 with EF 3.1 (sentier-brightway, about 36 MB, about a minute) ...")
    info = bafu2026.install()
    print(f"Done: project {info['project']}, {info['processes']} activities, {info['methods']} methods. {info['citation']}")


if __name__ == "__main__":
    main()
    if "--bafu-2026" in sys.argv[1:]:
        main_2026()
