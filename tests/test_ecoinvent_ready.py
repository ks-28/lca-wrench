"""Projects without BAFU (ecoinvent, EF): the app opens with a sensible method."""

from lca_wrench import service as s

ECOINVENT_LIKE = [
    ("CML v4.8 2016", "acidification", "acidification (incl. fate, average Europe total, A&B)"),
    ("EF v3.1", "climate change", "global warming potential (GWP100)"),
    ("IPCC 2013", "climate change", "GWP 100a"),
    ("ecoinvent-3.10", "IPCC 2021", "climate change: fossil", "global warming potential (GWP100)"),
    ("ecoinvent-3.10", "IPCC 2021", "climate change: total (excl. biogenic CO2)", "global warming potential (GWP100)"),
    ("ecoinvent-3.10", "IPCC 2021 no LT", "climate change: total (excl. biogenic CO2)", "global warming potential (GWP100)"),
    ("ecoinvent-3.10", "IPCC 2021", "climate change: total (excl. biogenic CO2)", "global warming potential (GWP20)"),
]


def test_default_method_is_climate_change_gwp100_of_the_newest_ipcc_as_total():
    assert s.default_method(ECOINVENT_LIKE) == list(ECOINVENT_LIKE[4])


def test_default_method_without_ipcc():
    assert s.default_method(ECOINVENT_LIKE[:3]) == list(ECOINVENT_LIKE[2])  # IPCC 2013 before EF
    assert s.default_method(ECOINVENT_LIKE[:2]) == list(ECOINVENT_LIKE[1])
    assert s.default_method([("ReCiPe 2016", "water use")]) == ["ReCiPe 2016", "water use"]
    assert s.default_method([]) is None


def test_this_apps_climate_method_wins_in_bafu_projects():
    assert s.default_method(ECOINVENT_LIKE + [s.CLIMATE_METHOD]) == list(s.CLIMATE_METHOD)
