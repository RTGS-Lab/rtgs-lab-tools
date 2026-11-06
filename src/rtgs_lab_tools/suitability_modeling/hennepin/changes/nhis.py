"""Natural Heritage Information System (NHIS) occurrence, per section, area-weighted.

Rule, Meaghan Dietrich 2026-11-02 (thread:0000000000036996): "the parcel should receive a score based
on the weight by percent of total acreage in each section". The parcel value is the sum over
sections of (section value x share of the parcel's in-section area).

Her field name Count_of_SpObs is not in the .dbf. Candidate fields: Polygon_Co (integer) and
sum_Area_S. Which one is the count is [NEEDS CONFIRM]; both are built, the config picks one.

Within-category weight 0.30 comes from the 2019 scoring document, "NHIS Occurrence (30%)". The
scale setting maps the area-weighted value to 0-1:
  linear: value / county maximum
  cap_p99: min(value, 99th percentile of parcels above 0) / that percentile
  log: log(1 + value) / log(1 + county maximum)
"""

import numpy as np
import pandas as pd
import pyogrio
import shapely

from ..geometry import overlap_areas

CHANGE_ID = "nhis"
INPUT = ("NHIS_Value", "Natural Heritage Information System Occurrence", "WP", 0.30, 1)


def build(ctx):
    s = pyogrio.read_dataframe(ctx.delivered["nhis_shp"], force_2d=True).to_crs(26915)
    sections = shapely.make_valid(s.geometry.to_numpy())
    pairs = overlap_areas(ctx.parcels_valid, sections)
    pairs = pairs[pairs.area > 0]
    pairs["Polygon_Co"] = s.Polygon_Co.to_numpy()[pairs.layer]
    pairs["sum_Area_S"] = s.sum_Area_S.to_numpy()[pairs.layer]
    grouped = pairs.groupby("parcel")
    covered = grouped["area"].sum()
    out = pd.DataFrame(index=range(len(ctx.parcels_valid)))
    out["NHIS_sections_crossed"] = grouped.size().reindex(out.index, fill_value=0)
    out["NHIS_covered_m2"] = covered.reindex(out.index, fill_value=0.0)
    for field in ("Polygon_Co", "sum_Area_S"):
        weighted = (pairs[field] * pairs["area"]).groupby(pairs["parcel"]).sum() / covered
        out[f"NHIS_aw_{field}"] = weighted.reindex(out.index, fill_value=0.0)
    out["NHIS_cover_share"] = out.NHIS_covered_m2 / shapely.area(ctx.parcels_valid)
    return out


def scaled(values, scale):
    v = np.asarray(values, dtype=float)
    if scale == "linear":
        return v / v.max()
    if scale == "cap_p99":
        cap = float(np.percentile(v[v > 0], 99))
        return np.minimum(v, cap) / cap
    if scale == "log":
        return np.log1p(v) / np.log1p(v.max())
    raise ValueError(scale)


def apply(values, frames, setting):
    """setting: dict(field=Polygon_Co|sum_Area_S, scale=linear|cap_p99|log)."""
    f = frames[CHANGE_ID]
    values["NHIS_Value"] = scaled(f[f"NHIS_aw_{setting['field']}"].to_numpy(), setting["scale"])
