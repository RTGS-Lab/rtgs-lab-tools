"""Hennepin V2 scoring pieces, on small synthetic tables. Runs without the county data."""

import numpy as np
import pandas as pd
import pytest
import shapely

from rtgs_lab_tools.suitability_modeling.hennepin.breaks import natural_breaks
from rtgs_lab_tools.suitability_modeling.hennepin.changes.natural_spaces import distance_class
from rtgs_lab_tools.suitability_modeling.hennepin.changes.nhis import scaled
from rtgs_lab_tools.suitability_modeling.hennepin.changes.risk_of_development import terciles
from rtgs_lab_tools.suitability_modeling.hennepin.geometry import overlap_areas
from rtgs_lab_tools.suitability_modeling.hennepin.score import score
from rtgs_lab_tools.suitability_modeling.hennepin.spec import INPUTS


def _values(n=4):
    rng = np.random.default_rng(1)
    v = pd.DataFrame({i[0]: rng.integers(0, 3, n).astype(float) for i in INPUTS})
    v.iloc[0] = 0.0  # the county has parcels scoring 0 on each category's inputs
    return v


def test_points_add_to_overall_and_rank_descends():
    res, scaling = score(_values(40), list(INPUTS))
    points = res[[f"pts_{i[0]}" for i in INPUTS]].sum(axis=1)
    assert np.allclose(points, res.Overall_Value)
    ordered = res.sort_values("Rank").Overall_Value.round(4)
    assert (ordered.diff().dropna() <= 0).all()
    assert sum(s["weight"] for s in scaling.values()) == pytest.approx(1)


def test_distance_class_matches_v1_bins():
    d = np.array([0, 30.47, 30.48, 804.66, 804.67, 1609.33, 1609.34, 5000])
    assert distance_class(d).tolist() == [3, 3, 2, 2, 1, 1, 0, 0]


def test_area_weighted_section_value():
    # A parcel three quarters in a 35-count section, one quarter in a 0-count section.
    parcel = np.array([shapely.box(0, 0, 4, 1)])
    sections = np.array([shapely.box(0, 0, 3, 1), shapely.box(3, 0, 10, 1)])
    pairs = overlap_areas(parcel, sections)
    counts = np.array([35, 0])[pairs.layer]
    assert (counts * pairs.area).sum() / pairs.area.sum() == pytest.approx(26.25)


def test_nhis_scales_stay_in_0_1():
    v = np.array([0.0, 1, 2, 3, 147])
    for scale in ("linear", "cap_p99", "log"):
        out = scaled(v, scale)
        assert out.min() == 0 and out.max() == pytest.approx(1)


def test_risk_terciles_score_only_at_risk():
    p = np.array([.01, .02, .03, .04, .05, .06, np.nan])
    at_risk = np.array([True] * 6 + [False])
    out, _, _ = terciles(p, at_risk)
    assert out.tolist() == [1, 1, 2, 2, 3, 3, 0]


def test_natural_breaks_finds_gaps():
    v = np.concatenate([np.full(50, 1.0), np.full(50, 5.0), np.full(50, 9.0)])
    assert natural_breaks(v, k=3, step=0.01) == pytest.approx([1.0, 5.0, 9.0])
