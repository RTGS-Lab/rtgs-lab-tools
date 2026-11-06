"""Bee habitat, Hennepin's 2026-10-06 delivery compared with the 2020 layer v1 used.

build() tests whether Bee_Habitat_Areas.shp differs from Bee_Habitat_ANALYSIS. If the classes and
geometry are the same, the change is a no-op and a re-run would reproduce v1's Bee_Value. If they
differ, build() stops, because the parcel overlay is not written for that case.

Kristine's 10/30 notes also name a Rusty Patched Bumble Bee update "in the spreadsheet" and a UMN
Bee Lab check. Neither has reached UMN as data. The spreadsheet on hand is the 7/29 copy.
"""

import hashlib

import pandas as pd
import pyogrio
import shapely

CHANGE_ID = "bee_habitat"


def build(ctx):
    a = pyogrio.read_dataframe(ctx.gdb, layer="Bee_Habitat_ANALYSIS", force_2d=True)
    b = pyogrio.read_dataframe(ctx.delivered["bee_shp"], force_2d=True)
    a = a.sort_values("Bee_Habitat_SCORE").reset_index(drop=True)
    b = b.sort_values("Bee_Habita").reset_index(drop=True)
    tol = shapely.equals_exact(shapely.normalize(a.geometry.to_numpy()),
                               shapely.normalize(b.geometry.to_numpy()), tolerance=0.01)
    same_class = (a.Bee_Habitat_SCORE.to_numpy() == b.Bee_Habita.to_numpy()).all()
    wkb = [hashlib.sha256(shapely.to_wkb(x)).hexdigest()[:16] for x in b.geometry]
    row = {
        "classes_equal": bool(same_class),
        "geometry_equal_within_1cm": bool(tol.all()),
        "area_diff_m2": float(abs(a.geometry.area.sum() - b.geometry.area.sum())),
        "wkb_2026": ";".join(wkb),
    }
    if not (row["classes_equal"] and row["geometry_equal_within_1cm"]):
        raise ValueError(f"bee layers differ, overlay needed: {row}")
    return pd.DataFrame([row])


def apply(values, frames, setting):
    """No-op by build()'s test: the delivered layer is the 2020 layer."""
    if setting != "delivered_2026":
        raise ValueError(setting)
