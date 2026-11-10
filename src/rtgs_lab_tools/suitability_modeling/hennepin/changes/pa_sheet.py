"""Protected Areas per the Scoring Review tab (rows 2-12, 40).

Sheet, row 2 "Proposed Layer Query": use State Administered Lands in place of WMAs, AMAs and SNAs;
merge the protected areas into one layer; clip to county + 1 mile; Near analysis from each
parcel; score 3 (encompasses or within 100 ft) / 2 (1/2 mile) / 1 (1 mile) / 0. Row 40: the 2020
Protected Areas composite is replaced by the layers aggregated above. Near measures to the edge,
so this module uses edge distance, not v1's centroid-to-centroid.

Sources (sheet row): 2026 easement compilation (2), USFWS realty (3), Parks of Natural Resource
Significance (4), State Administered Lands (5-7, 9), TNC Lands (8), Three Rivers gap parks (10).
Row 11 (TNC transferred) is removed. Row 12 PAD-US subset has its own scale: 1 within 100 ft,
0.5 within 1 mile; PA_S is the higher of the two scores, on the same 0-3 scale (divisor 3).
"""

import geopandas as gpd
import numpy as np
import pyogrio

from ..sheet_common import distance_points, edge_distance, frame, read_public

CHANGE_ID = "pa_sheet"
INPUT = ("PA_S", "Protected Areas (Scoring Review set)", "SC", 0.50, 3)
SHEET_SOURCES = ["easements_2026", "usfws", "parks_nr", "sal", "tnc", "trpd_gap"]


def sheet_layers(ctx):
    """name -> GeoSeries in EPSG:26915. Shared with exclusions.py (protected mask)."""
    d = ctx.delivered
    ease = pyogrio.read_dataframe(d["easements_gdb"], layer="All_Known_Easements_Combined_2026",
                                  force_2d=True).to_crs(26915)
    parks = pyogrio.read_dataframe(d["parks_gdb"], layer="Parks_NaturalResources_Analysis",
                                   force_2d=True).to_crs(26915)
    parks = parks[parks.NaturalResources_Category != "Amenities"]
    return {
        "easements_2026": ease.geometry,
        "usfws": read_public("usfws_national_realty_boundaries").geometry,
        "parks_nr": parks.geometry,
        "sal": read_public("state_administered_lands").geometry,
        "tnc": read_public("TNC_lands").geometry,
        "trpd_gap": pyogrio.read_dataframe(d["trpd_gap_shp"], force_2d=True).to_crs(26915).geometry,
        "padus_nrvalue": pyogrio.read_dataframe(d["padus_shp"], force_2d=True).to_crs(26915).geometry,
        "pa_2020": pyogrio.read_dataframe(ctx.gdb, layer="Protected_Areas_ANALYSIS",
                                          force_2d=True).to_crs(26915).geometry,
    }


def build(ctx):
    lay = sheet_layers(ctx)
    merged = np.concatenate([lay[s].to_numpy() for s in SHEET_SOURCES])
    out = frame(
        ctx,
        PA_S_edge_sheet_m=edge_distance(ctx, merged),
        PA_S_edge_padus_m=edge_distance(ctx, lay["padus_nrvalue"].to_numpy()),
        PA_S_edge_2020_m=edge_distance(ctx, lay["pa_2020"].to_numpy()),
    )
    out.attrs["features"] = {k: int(len(v)) for k, v in lay.items()}
    return out


def apply(values, frames, setting):
    """setting: dict(padus=bool, plus_2020=bool)."""
    f = frames[CHANGE_ID]
    d = f.PA_S_edge_sheet_m.to_numpy()
    if setting.get("plus_2020"):
        d = np.minimum(d, f.PA_S_edge_2020_m.to_numpy())
    pts = distance_points(d, (3, 2, 1))
    if setting.get("padus", True):
        pts = np.maximum(pts, distance_points(f.PA_S_edge_padus_m.to_numpy(), (1, 0.5, 0.5)))
    values["PA_S"] = pts
