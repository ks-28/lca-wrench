# Methods across lists of elementary flows (flow mapping)

A project can hold data on two lists of elementary flows: ecoinvent's (`biosphere3`, also EXIOBASE as imported here) and
the EF 3.1 reference list (BAFU 2026 through sentier-brightway, `ef-3.1-biosphere`). Each method is implemented on one
list: the methods ecoinvent ships on `biosphere3`, sentier's EF 3.1 on `ef-3.1-biosphere`. On a product of the other
list such a method finds no factor and gives 0, which looks like a result. In a project with ecoinvent 3.12 (with its
LCIA methods), BAFU 2026 and EXIOBASE there were 548 methods on `biosphere3` only, 85 also on EXIOBASE's flows and 25
on `ef-3.1-biosphere` only, so no method covered a BAFU and an ecoinvent product at once.

## What LCA Wrench does

- **Compare** shows for each product whether the method has factors for its flows (`lca_wrench/flowmap.py`,
  `coverage`): its own, partly through the flow mapping (marked ≈), or none (then "–" and the list it lacks, not 0). In
  Compare, only the methods with factors for all products compared are offered (the open one stays, marked ⚠). Lists
  no method has factors on (BAFU 2026's residual flows) do not count.
- **Flow mapping:** `ecoinvent-3.11-biosphere-EF-3.1-biosphere` (randonneur_data; GLAD mappings plus manual and
  algorithmic matches; CC BY 4.0; see `lca_wrench/data/flowmaps/README.md`) matches 9238 ecoinvent flows to EF 3.1 flows
  by UUID; 9228 have the same unit and are used. A method that covers one list gets factors for the matched flows of the
  other: an EF flow takes the mean factor of the ecoinvent flows matched to it, an ecoinvent flow the factor of its EF
  flow. Only flows of a list the method has no factor on at all are filled, so its own factors (and zeros) stay. The
  mapping is applied in the calculation (engine, cross-check with bw2calc, Monte Carlo and sensitivity) and never
  written into the project. It is on by default; the switch is in Compare and applies to all calculations.

## Only where it holds

EF 3.1 is implemented on both lists in such a project, so each direction was checked against the native implementation
(ratio mapped / native, 7 BAFU and 8 ecoinvent products: electricity, cement, steel, transport, heat, tap water,
wheat, polyethylene):

| Kind of impact | ecoinvent methods on EF flows (BAFU) | EF methods on ecoinvent flows | Filled |
|---|---|---|---|
| Climate change (also fossil, biogenic, land use) | 1.00 | 1.00 (land use 1.00–1.03) | yes |
| Acidification, eutrophication (freshwater, terrestrial), photochemical ozone, land use | 1.00 | 1.00 | yes |
| Eutrophication marine | 0.97–1.00 | 1.00–1.21 | yes |
| Ionising radiation | 0.96–0.99 | 1.00 | yes |
| Ozone depletion | 0.32–0.93 | 1.00–1.05 | only EF → ecoinvent |
| Mineral resources | 1.00 | 0.34–1.00 | only ecoinvent → EF |
| Particulate matter | 0.77–0.98 | 0.85–0.94 | no |
| Toxicity | 0.08–0.98 | 0.75–3.1 | no |
| Water use | 0.00–0.28 | 0.98–298 | no |
| Energy resources (kg against MJ) | 0 | 0 | no |

The kind of impact is the topic of the category (`overview.topic`), so the rule applies to every method family (ReCiPe,
IPCC, Ecological Scarcity and so on); single scores and endpoints that add up several kinds are never filled. On real
data (the project above): a BAFU 2026 product is covered by 318 instead of 25 methods (293 through the mapping), a BAFU
and an ecoinvent product together by 305 instead of none. Ecoinvent's IPCC 2021 on BAFU's Portuguese low-voltage
electricity gives 0.20238 kg CO₂-eq, sentier's EF 3.1 natively 0.20251.

## Tests

`tests/test_backgrounds.py` uses two small flow lists carrying real UUIDs of the mapping: both directions, water not
filled, Compare's coverage and method list, the switch, the cross-check and Monte Carlo.

A related mechanism, which completes factors within one list for sub-compartments, is described in
[completed-factors.md](completed-factors.md).
