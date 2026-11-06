"""Protected Areas: inputs delivered since v1, each with its own toggle.

v1 method kept: parcel centroid to nearest polygon-part centroid, v1 bins. A new source adds its
part centroids to the 2020 set, so it can only raise PA_Value. The sources are toggled one at a time
by the `sources` setting of each config entry; apply() takes the minimum distance over those on.
"""

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio

from .natural_spaces import distance_class, nearest_distance

CHANGE_ID = "protected_areas"


def _parts(g, repair=True):
    """Polygon parts. repair=False keeps the geometry as v1 read it, so 2020 centroids match v1."""
    g = g.to_crs(26915)
    if repair:
        g = g.set_geometry(g.make_valid())
    parts = g.explode(index_parts=False).reset_index(drop=True)
    return parts[parts.geom_type == "Polygon"]


def sources(ctx):
    """Source name -> polygon parts. Easements overlap themselves, so they are dissolved first."""
    d = ctx.delivered
    easements = pyogrio.read_dataframe(d["easements_gdb"], layer="All_Known_Easements_Combined_2026",
                                       force_2d=True).to_crs(26915)
    easements = gpd.GeoDataFrame(geometry=[easements.make_valid().union_all()], crs=26915)
    parks = pyogrio.read_dataframe(d["parks_gdb"], layer="Parks_NaturalResources_Analysis",
                                   force_2d=True)
    parks = parks[parks.NaturalResources_Category != "Amenities"]
    return {
        "2020": _parts(pyogrio.read_dataframe(ctx.gdb, layer="Protected_Areas_ANALYSIS",
                                              force_2d=True), repair=False),
        "easements_2026": _parts(easements),
        "trpd_gap": _parts(pyogrio.read_dataframe(d["trpd_gap_shp"], force_2d=True)),
        "parks_nr": _parts(parks),
        "padus_nrvalue": _parts(pyogrio.read_dataframe(d["padus_shp"], force_2d=True)),
    }


def build(ctx):
    out = {}
    counts = {}
    for name, parts in sources(ctx).items():
        counts[name] = len(parts)
        out[f"PA_dist_{name}_m"] = nearest_distance(ctx.centroids, parts.geometry.centroid)
        out[f"PA_edge_{name}_m"] = nearest_distance(ctx.parcels.geometry, parts.make_valid())
    frame = pd.DataFrame(out)
    frame.attrs["part_counts"] = counts
    return frame


def apply(values, frames, setting):
    """setting: dict(sources=[names on top of 2020], method=part_centroid|edge)."""
    f = frames[CHANGE_ID]
    kind = "edge" if setting.get("method") == "edge" else "dist"
    cols = [f"PA_{kind}_{s}_m" for s in ["2020"] + list(setting["sources"])]
    values["PA_Value"] = distance_class(f[cols].min(axis=1).to_numpy())
