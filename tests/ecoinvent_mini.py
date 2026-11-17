"""A tiny ecoinvent release in the format of ecoinvent.org, to test the ecoinvent import without a licence.

Two unit processes (ecoSpold02, as in the real «ecoinvent 3.10_cutoff_ecoSpold02.7z»), the real elementary flows of
ecoinvent 3.9 that bw2io ships, and an LCIA implementation file with one method:

- widget production: 1 kg widget, needs 0.5 kWh electricity, emits 2 kg CO2 (fossil, non-urban air)
- electricity production: 1 kWh electricity, emits 0.1 kg CO2 (fossil, urban air)
- method ("ecoinvent-3.10", "TEST", "climate change", "GWP 100a"): both CO2 flows count 1 kg CO2-eq per kg

So 1 kg widget = 2 + 0.5 * 0.1 = 2.05 kg CO2-eq.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import bw2io
import openpyxl
import py7zr

VERSION, SYSTEM_MODEL = "3.10", "cutoff"
METHOD = (f"ecoinvent-{VERSION}", "TEST", "climate change", "GWP 100a")
WIDGET_SCORE = 2.05

CO2_URBAN = "f9749677-9c9f-4678-ab55-c607dfdc2cb9"
CO2_NONURBAN = "aa7cac3a-3625-41d4-bc54-33e2cf11ec46"
WIDGET = ("11111111-0000-0000-0000-000000000001", "22222222-0000-0000-0000-000000000001")  # activity, product
ELEC = ("11111111-0000-0000-0000-000000000002", "22222222-0000-0000-0000-000000000002")
KG, KWH = "487df68b-4994-4027-8fdc-a4dc298257b7", "b9c6d4d4-0f0e-4e2d-9b3b-1b3f1f1f1f1f"

NS = "http://www.EcoInvent.org/EcoSpold02"


def _dataset(act, name, product, unit_id, unit, location, inputs, emissions):
    flows = [f"""      <intermediateExchange id="{act[0][:8]}-aaaa-0000-0000-000000000000" unitId="{unit_id}" amount="1" intermediateExchangeId="{act[1]}" productionVolumeAmount="100">
        <name xml:lang="en">{product}</name>
        <unitName xml:lang="en">{unit}</unitName>
        <classification classificationId="39b0f0ab-1a2f-401b-9f4d-6e39400760a4">
          <classificationSystem xml:lang="en">By-product classification</classificationSystem>
          <classificationValue xml:lang="en">allocatable product</classificationValue>
        </classification>
        <outputGroup>0</outputGroup>
      </intermediateExchange>"""]
    for i, (other, oname, ounit_id, ounit, amount) in enumerate(inputs):
        flows.append(f"""      <intermediateExchange id="{act[0][:8]}-bbbb-0000-0000-00000000000{i}" unitId="{ounit_id}" amount="{amount}" intermediateExchangeId="{other[1]}" activityLinkId="{other[0]}">
        <name xml:lang="en">{oname}</name>
        <unitName xml:lang="en">{ounit}</unitName>
        <inputGroup>5</inputGroup>
      </intermediateExchange>""")
    for i, (flow, sub, amount) in enumerate(emissions):
        flows.append(f"""      <elementaryExchange id="{act[0][:8]}-cccc-0000-0000-00000000000{i}" unitId="{KG}" amount="{amount}" elementaryExchangeId="{flow}">
        <name xml:lang="en">Carbon dioxide, fossil</name>
        <unitName xml:lang="en">kg</unitName>
        <compartment subcompartmentId="00000000-0000-0000-0000-000000000000">
          <compartment xml:lang="en">air</compartment>
          <subcompartment xml:lang="en">{sub}</subcompartment>
        </compartment>
        <outputGroup>4</outputGroup>
      </elementaryExchange>""")
    body = "\n".join(flows)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<ecoSpold xmlns="{NS}">
  <childActivityDataset>
    <activityDescription>
      <activity id="{act[0]}" activityNameId="{act[0][:8]}-dddd-0000-0000-000000000000" inheritanceDepth="0" type="1" specialActivityType="0">
        <activityName xml:lang="en">{name}</activityName>
        <generalComment><text xml:lang="en" index="0">Test data, not ecoinvent.</text></generalComment>
      </activity>
      <classification classificationId="27f6acbc-2350-450e-9762-1ce00e12ecba">
        <classificationSystem xml:lang="en">ISIC rev.4 ecoinvent</classificationSystem>
        <classificationValue xml:lang="en">0000:Test</classificationValue>
      </classification>
      <geography geographyId="00000000-0000-0000-0000-000000000000"><shortname xml:lang="en">{location}</shortname></geography>
      <technology technologyLevel="3" />
      <timePeriod startDate="2020-01-01" endDate="2024-12-31" isDataValidForEntirePeriod="true" />
    </activityDescription>
    <flowData>
{body}
    </flowData>
    <modellingAndValidation>
      <representativeness systemModelId="06590a66-662a-4885-8494-ad0cf410f956">
        <systemModelName xml:lang="en">Allocation, cut-off by classification</systemModelName>
      </representativeness>
    </modellingAndValidation>
    <administrativeInformation>
      <dataEntryBy personId="00000000-0000-0000-0000-000000000000" personName="Test" personEmail="test@example.org" />
      <dataGeneratorAndPublication personId="00000000-0000-0000-0000-000000000000" personName="Test" personEmail="test@example.org" dataPublishedIn="0" isCopyrightProtected="false" accessRestrictedTo="0" />
    </administrativeInformation>
  </childActivityDataset>
</ecoSpold>
"""


def write_release(folder: Path) -> Path:
    """The unpacked release (datasets + MasterData) in `folder`."""
    (folder / "datasets").mkdir(parents=True)
    (folder / "MasterData").mkdir()
    shutil.copy(Path(bw2io.__file__).parent / "data" / "lci" / "ecoinvent elementary flows 3.9.xml",
                folder / "MasterData" / "ElementaryExchanges.xml")
    products = [(WIDGET[1], "widget", "kg"), (ELEC[1], "electricity, low voltage", "kWh")]
    (folder / "MasterData" / "IntermediateExchanges.xml").write_text(
        f'<?xml version="1.0" encoding="utf-8"?>\n<validIntermediateExchanges xmlns="{NS}">\n'
        + "".join(f'  <intermediateExchange id="{i}" unitId="{KG}"><name xml:lang="en">{n}</name>'
                  f'<unitName xml:lang="en">{u}</unitName></intermediateExchange>\n' for i, n, u in products)
        + "</validIntermediateExchanges>\n", encoding="utf-8")
    (folder / "datasets" / f"{WIDGET[0]}_{WIDGET[1]}.spold").write_text(_dataset(
        WIDGET, "widget production", "widget", KG, "kg", "CH",
        [(ELEC, "electricity, low voltage", KWH, "kWh", 0.5)], [(CO2_NONURBAN, "non-urban air or from high stacks", 2)]),
        encoding="utf-8")
    (folder / "datasets" / f"{ELEC[0]}_{ELEC[1]}.spold").write_text(_dataset(
        ELEC, "electricity production", "electricity, low voltage", KWH, "kWh", "CH",
        [], [(CO2_URBAN, "urban air close to ground", 0.1)]), encoding="utf-8")
    return folder


def write_lcia(path: Path) -> Path:
    wb = openpyxl.Workbook()
    ind = wb.active
    ind.title = "Indicators"
    ind.append(["Method", "Category", "Indicator", "Indicator Unit"])
    ind.append(list(METHOD[1:]) + ["kg CO2-Eq"])
    cfs = wb.create_sheet("CFs")
    cfs.append(["Method", "Category", "Indicator", "Name", "Compartment", "Subcompartment", "CF"])
    for sub in ("urban air close to ground", "non-urban air or from high stacks"):
        cfs.append(list(METHOD[1:]) + ["Carbon dioxide, fossil", "air", sub, 1.0])
    wb.save(path)
    return path


def write_archives(folder: Path) -> tuple[Path, Path]:
    """The two files as downloaded from ecoinvent.org: ecoSpold02 archive and LCIA implementation archive."""
    release = write_release(folder / "unpacked")
    lci = folder / f"ecoinvent {VERSION}_{SYSTEM_MODEL}_ecoSpold02.7z"
    with py7zr.SevenZipFile(lci, "w") as archive:
        archive.writeall(release / "datasets", "datasets")
        archive.writeall(release / "MasterData", "MasterData")
    xlsx = write_lcia(folder / f"LCIA_implementation_{VERSION}.xlsx")
    lcia = folder / f"ecoinvent {VERSION}_LCIA_implementation.7z"
    with py7zr.SevenZipFile(lcia, "w") as archive:
        archive.write(xlsx, xlsx.name)
    return lci, lcia
