"""Scoring Review V2 (2026-11-10 tab) rules on synthetic tables, and the config that specifies it.

Runs without county data. Sheet rows refer to the "Scoring Review and Recommendations" tab.
"""

import numpy as np
import pandas as pd
import pytest

from rtgs_lab_tools.suitability_modeling.hennepin.changes import (
    risk_of_development,
    sheet_weights,
    size_sheet,
    water_sheet,
)
from rtgs_lab_tools.suitability_modeling.hennepin.context import load_config
from rtgs_lab_tools.suitability_modeling.hennepin.run import ranked, variant_list
from rtgs_lab_tools.suitability_modeling.hennepin.score import score
from rtgs_lab_tools.suitability_modeling.hennepin.sheet_common import distance_points
from rtgs_lab_tools.suitability_modeling.hennepin.spec import CATEGORIES, INPUTS
from rtgs_lab_tools.suitability_modeling.hennepin.variants import apply_changes

TAB = "Scoring Review and Recommendations"


def test_distance_points_rows_2_and_12():
    d = np.array([0, 30.47, 30.48, 804.66, 804.67, 1609.33, 1609.34, np.inf])
    assert distance_points(d, (3, 2, 1)).tolist() == [3, 3, 2, 2, 1, 1, 0, 0]
    # PAD-US, row 12: adjacent (100 ft) 1, within 1 mile 0.5
    assert distance_points(d, (1, 0.5, 0.5)).tolist() == [1, 1, .5, .5, .5, .5, 0, 0]


def test_absolute_size_bins_row_24():
    acres = np.array([0, 4.99, 5, 9.9, 10, 29.9, 30, 49.9, 50, 79.9, 80, 500])
    frames = {"size_sheet": pd.DataFrame({"SZ_S_acres": acres})}
    v = pd.DataFrame(index=range(len(acres)))
    size_sheet.apply(v, frames, "absolute_bins")
    assert v.SZ_S.tolist() == [0, 0, .5, .5, 1, 1, 2, 2, 3, 3, 4, 4]


def test_risk_continuous_row_35():
    f = pd.DataFrame({"ROD_at_risk": [True, False, True], "ROD_p_sub24": [0.2, 0.9, np.nan],
                      "ROD_farm": [False, False, False]})
    v = pd.DataFrame(index=range(3))
    risk_of_development.apply(v, {"risk_of_development": f}, "continuous")
    assert v.ROD_Value.tolist() == [0.2, 0.0, 0.0]


def test_floodplain_points_row_43():
    g = pd.DataFrame({"FLD_ZONE": ["AE", "A", "X", "X", "AO", None],
                      "ZONE_SUBTY": [None, None, "0.2 PCT ANNUAL CHANCE FLOOD HAZARD",
                                     "AREA OF MINIMAL FLOOD HAZARD", None, None]})
    assert water_sheet.floodplain_points(g).tolist() == [2, 2, 1, 0, 2, 0]


def test_ranked_skips_excluded_parcels():
    overall = np.array([50.0, 40.0, 60.0, 10.0])
    excluded = np.array([False, False, True, False])
    assert ranked(None, overall, excluded).tolist() == [1, 2, 0, 3]


def test_reweight_uses_fallback_when_change_off():
    values = pd.DataFrame({"PA_Value": [0, 3.0], "QC_S": [1.0, 0]})
    setting = {"inputs": {"PA_S": {"cat": "SC", "weight": .5, "div": 3, "fallback": "PA_Value"},
                          "QC_S": {"cat": "HQ", "weight": .1, "div": 1},
                          "COA_S": {"cat": "WP", "weight": .08, "div": 1}}}
    inputs, used = sheet_weights.reweight(values, list(INPUTS), setting)
    assert [i[0] for i in inputs] == ["PA_Value", "QC_S"]
    assert used == {"PA_S": "PA_Value", "QC_S": "QC_S", "COA_S": None}


# --- the config that specifies V2 --------------------------------------------------------------

def test_sheet_weights_sum_to_one_per_category():
    w = load_config()["changes"]["sheet_weights"]["setting"]["inputs"]
    sums = {}
    for spec in w.values():
        sums[spec["cat"]] = sums.get(spec["cat"], 0) + spec["weight"]
    assert set(sums) == {k for k, *_ in CATEGORIES}
    assert all(s == pytest.approx(1.0) for s in sums.values())
    # removed by the sheet: Relative Size (row 23, inside Size_Value), groundwater recharge (row 46)
    assert "GW_Value" not in w and "Size_Value" not in w


def test_every_v2_entry_names_its_sheet_cells():
    config = load_config()
    for cid, e in config["changes"].items():
        refs = e.get("sheet") or []
        assert refs, f"{cid} has no sheet: annotation"
        for r in refs:
            assert r["tab"] == TAB and 2 <= r["row"] <= 47 and r["col"], (cid, r)
    for field, spec in config["changes"]["sheet_weights"]["setting"]["inputs"].items():
        assert spec["sheet"]["tab"] == TAB and 2 <= spec["sheet"]["row"] <= 47, field


def test_a343a98_variant_is_kept():
    v = variant_list(load_config())
    assert v["v2_a343a98"]["nhis"] == {"field": "Polygon_Co", "scale": "cap_p99"}
    assert "sheet_weights" in v["v2"] and "sheet_weights" not in v["v2_a343a98"]


def test_v2_input_list_matches_the_sheet():
    """Full V2 on a tiny table: every weighted input comes from a sheet change, none from GW."""
    config = load_config()
    n = 6
    rng = np.random.default_rng(2)
    table = pd.DataFrame({i[0]: rng.integers(0, 3, n).astype(float) for i in INPUTS})
    table.iloc[3] = 0.0  # parcel 3 scores 0 on every input it keeps from v1
    frames = {
        "pa_sheet": pd.DataFrame({"PA_S_edge_sheet_m": [0, 100, 900, 2000, 0, 10.0],
                                  "PA_S_edge_padus_m": [np.inf] * n, "PA_S_edge_2020_m": [0.0] * n}),
        "ns_sheet": pd.DataFrame({"NS_S_edge_mecc_m": [0, 5000, 900, 2000, 0, 10.0]}),
        "qc_sheet": pd.DataFrame({"QC_S_edge_npc_m": [0, 50, 9, 2000, 0, 10.0],
                                  "QC_S_edge_mbs_m": [np.inf] * n}),
        "size_sheet": pd.DataFrame({"SZ_S_acres": [1, 6, 12, 35, 60, 90.0]}),
        "potential_easements": pd.DataFrame({"PEA_edge_m": [0, 500, 900, 9000, 0, 10.0]}),
        "nhis": pd.DataFrame({"NHIS_aw_Polygon_Co": [0, 1, 2, 0, 4, 5.0],
                              "NHIS_aw_sum_Area_S": [0.0] * n}),
        "wildlife_sheet": pd.DataFrame({"WAN_S_rank": [0, 1, 5, 0, 0, 2.0], "COA_S_in": [0, 1, 0, 0, 1, 0.0],
                                        "RPBB_S_zone": [0, 2, 1, 0, 0, 0.0], "Bird_S_in": [0, 1, 0, 0, 0, 0.0]}),
        "important_waters": pd.DataFrame({"LBS_S_edge_m": [0, 5000, 900, 2000, 0, 10.0],
                                          "SHL_S_edge_m": [np.inf] * n}),
        "risk_of_development": pd.DataFrame({"ROD_at_risk": [True, False] * 3,
                                             "ROD_p_sub24": [.1, .2, .3, .4, .5, .6],
                                             "ROD_farm": [False] * n}),
        "water_sheet": pd.DataFrame({"SB_S_share": [0, .1, .2, 1, 0, .5], "SB_S_share_50ft": [0.0] * n,
                                     "FP_S_points": [0, 2, 1, 0, 0, 2.0], "NWI_S_share": [0, .3, 0, 1, 0, 0],
                                     "HW_S_gdb2020": [0, 1, 0, 1, 0, 0.0], "HW_S_level08": [0.0] * n,
                                     "AQV_S_points": [0, 1, 2, 0, 0, 1.0]}),
    }
    active = variant_list(config)["v2"]
    values, inputs = apply_changes(table, frames, active, config)
    names = [i[0] for i in inputs]
    assert names == list(config["changes"]["sheet_weights"]["setting"]["inputs"])
    assert "GW_Value" not in names and "Size_Value" not in names and "HCWI_Value" not in names
    res, scaling = score(values, inputs)
    assert res.Overall_Value.between(0, 100).all()
