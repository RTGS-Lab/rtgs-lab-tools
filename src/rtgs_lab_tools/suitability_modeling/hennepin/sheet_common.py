"""Shared reads and overlays for the Scoring Review V2 change modules. No scoring rules here.

Layers come from fetch.py output: <public_root>/<registry key>/<key>.gpkg, EPSG:26915.
"""

import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely

from .context import load_config
from .geometry import overlap_areas, polygons_only, tile

FT100, MI_HALF, MI1 = 30.48, 804.67, 1609.34  # 100 ft, 1/2 mile, 1 mile in metres (v1 bins)


def public_path(key, suffix=""):
    root = Path(load_config()["public_root"])
    return root / key / f"{key}{suffix}.gpkg"


def read_public(key, suffix="", columns=None):
    p = public_path(key, suffix)
    if not p.exists():
        raise FileNotFoundError(f"{p}: run hennepin.fetch --only {key}")
    g = pyogrio.read_dataframe(p, columns=columns, force_2d=True)
    return g.to_crs(26915) if g.crs is not None else g.set_crs(26915)


def fetch_record(key):
    p = Path(load_config()["public_root"]) / key / "fetch.json"
    return json.loads(p.read_text()) if p.exists() else None


def polygon_parts(geoms):
    """Valid polygon parts of a geometry array (multipolygons exploded)."""
    parts = shapely.get_parts(shapely.make_valid(np.asarray(geoms)))
    parts = shapely.get_parts(parts)  # collections from make_valid
    return parts[shapely.get_type_id(parts) == 3]


def edge_distance(ctx, geoms):
    """Parcel polygon to nearest feature edge, metres; 0 when they overlap (ArcGIS Near). Beyond 1 mile
    every class scores 0, so the search stops there and farther parcels get inf."""
    parts = polygon_parts(geoms)
    if len(parts) == 0:
        return np.full(len(ctx.parcels), np.inf)
    a = gpd.GeoDataFrame(geometry=ctx.parcels_valid, crs=26915)
    b = gpd.GeoDataFrame(geometry=parts, crs=26915)
    j = gpd.sjoin_nearest(a, b, distance_col="d", max_distance=MI1 + 1.0)
    d = j.groupby(level=0)["d"].min().reindex(a.index)
    return d.fillna(np.inf).to_numpy()


def distance_points(d, points):
    """points = (inside 100 ft, inside 1/2 mile, inside 1 mile). Strict < as ArcGIS Near classes."""
    p100, phalf, p1 = points
    return np.select([d < FT100, d < MI_HALF, d < MI1], [p100, phalf, p1], 0.0)


def max_value_overlap(ctx, geoms, values):
    """Highest value among features whose overlap with the parcel has positive area."""
    geoms = shapely.make_valid(np.asarray(geoms))
    vals = np.asarray(values, dtype=float)
    keep = ~shapely.is_empty(geoms)
    geoms, vals = geoms[keep], vals[keep]
    out = np.zeros(len(ctx.parcels_valid))
    if len(geoms) == 0:
        return out
    # cut each feature into 2 km tiles: intersecting a parcel with a county-sized polygon is slow
    pieces, pvals = [], []
    for g, v in zip(geoms, vals):
        t = tile(polygons_only(g)) if shapely.area(g) > 4e6 else np.array([g], dtype=object)
        pieces.append(t)
        pvals.append(np.full(len(t), v))
    geoms, vals = np.concatenate(pieces), np.concatenate(pvals)
    pairs = overlap_areas(ctx.parcels_valid, geoms)
    pairs = pairs[pairs.area > 0]
    pairs["v"] = vals[pairs.layer.to_numpy()]
    best = pairs.groupby("parcel")["v"].max()
    out[best.index.to_numpy()] = best.to_numpy()
    return out


def area_share(ctx, geom):
    """Area of (parcel intersect geom) / parcel area, geom dissolved first so nothing counts twice."""
    pieces = tile(polygons_only(shapely.make_valid(geom)))
    parcels = ctx.parcels_valid
    pairs = overlap_areas(parcels, pieces)
    area = pairs.groupby("parcel")["area"].sum().reindex(range(len(parcels)), fill_value=0.0)
    return area.to_numpy(), np.minimum(area.to_numpy() / shapely.area(parcels), 1.0)


def frame(ctx, **cols):
    return pd.DataFrame(cols, index=range(len(ctx.parcels)))
