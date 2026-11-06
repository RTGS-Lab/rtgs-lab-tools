"""Natural Spaces fix.

v1 notebook BL_1.2 cell 6 takes the centroid of the un-exploded layer, one multipolygon with 1,091
parts, so every parcel is measured to a single point near the Medina/Plymouth line. BL_1.1
(Protected Areas) uses exploded parts. Setting `part_centroid` applies the Protected Areas method.
Setting `edge` measures parcel polygon to part polygon, which is what the 2019 scoring document
describes but v1 never did for either input.
"""

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio

CHANGE_ID = "natural_spaces"
BINS_M = (30.48, 804.67, 1609.34)  # 100 ft, 1/2 mile, 1 mile: BL_1.1 and BL_1.2


def distance_class(d):
    """3 / 2 / 1 / 0 by the v1 bins. Same comparison order as the v1 PA_Value function."""
    return np.select([d >= BINS_M[2], d >= BINS_M[1], d >= BINS_M[0]], [0, 1, 2], 3)


def nearest_distance(from_geoms, to_geoms, crs=26915):
    a = gpd.GeoDataFrame(geometry=np.asarray(from_geoms), crs=crs)
    b = gpd.GeoDataFrame(geometry=np.asarray(to_geoms), crs=crs)
    j = gpd.sjoin_nearest(a, b, distance_col="d")
    return j.groupby(level=0)["d"].min().reindex(a.index).to_numpy()


def build(ctx):
    ns = pyogrio.read_dataframe(ctx.gdb, layer="Natural_Spaces_ANALYSIS", force_2d=True)
    ns = ns.to_crs(26915)
    parts = ns.explode(index_parts=False).reset_index(drop=True)
    return pd.DataFrame(
        {
            "NS_dist_v1_point_m": ctx.centroids.distance(ns.geometry.centroid.iloc[0]).to_numpy(),
            "NS_dist_part_centroid_m": nearest_distance(ctx.centroids, parts.geometry.centroid),
            "NS_dist_edge_m": nearest_distance(ctx.parcels.geometry, parts.make_valid()),
        }
    )


def apply(values, frames, setting):
    f = frames[CHANGE_ID]
    if setting == "part_centroid":
        values["NS_Value"] = distance_class(f.NS_dist_part_centroid_m.to_numpy())
    elif setting == "edge":
        values["NS_Value"] = distance_class(f.NS_dist_edge_m.to_numpy())
    else:
        raise ValueError(setting)
