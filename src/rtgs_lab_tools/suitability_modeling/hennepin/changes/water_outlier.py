"""Water Resources outlier: SB_Value and HCWI_Value.

Both should be shares of parcel area, between 0 and 1. v1 runs to 194,933 and 6,391. BL_6.1 overlays
parcels with the layer, then spatial-joins the pieces back to the parcels with "intersects" and sums
piece areas, so each parcel also collects the pieces of every neighbour it touches.

reproduce_v1() repeats those notebook steps to test that cause against the stored values.
Setting `recompute`: area of (parcel intersect layer) / parcel area, no 50 m simplification.
Setting `clip`: keep the v1 values, cap at 1.
"""

import numpy as np
import pandas as pd
import pyogrio
import shapely

from ..geometry import overlap_areas, polygons_only, tile

CHANGE_ID = "water_outlier"


def _layer_union(gdb, layer):
    g = pyogrio.read_dataframe(gdb, layer=layer, force_2d=True).to_crs(26915)
    return shapely.union_all(shapely.make_valid(g.geometry.to_numpy()))


def _share(ctx, geom):
    pieces = tile(polygons_only(shapely.make_valid(geom)))
    parcels = ctx.parcels_valid
    pairs = overlap_areas(parcels, pieces)
    area = pairs.groupby("parcel")["area"].sum().reindex(range(len(parcels)), fill_value=0.0)
    return area.to_numpy(), area.to_numpy() / shapely.area(parcels)


def build(ctx):
    sb_area, sb = _share(ctx, _layer_union(ctx.gdb, "Shoreland_BufferAreas_ANALYSIS"))
    wet_area, wet = _share(ctx, _layer_union(ctx.gdb, "HCWI_ANALYSIS"))
    return pd.DataFrame(
        {
            "SB_area_m2": sb_area,
            "SB_share": np.minimum(sb, 1.0),
            "HCWI_area_m2": wet_area,
            "HCWI_share": np.minimum(wet, 1.0),
        }
    )


def apply(values, frames, setting):
    f = frames[CHANGE_ID]
    if setting == "recompute":
        values["SB_Value"] = f.SB_share.to_numpy()
        values["HCWI_Value"] = f.HCWI_share.to_numpy()
    elif setting == "clip":
        values["SB_Value"] = values["SB_Value"].clip(upper=1.0)
        values["HCWI_Value"] = values["HCWI_Value"].clip(upper=1.0)
    else:
        raise ValueError(setting)


def reproduce_v1(ctx, stored_sb, denominator):
    """Repeat BL_6.1 on all parcels: simplify 50 m, overlay, join pieces back, sum, divide."""
    g = pyogrio.read_dataframe(ctx.gdb, layer="Shoreland_BufferAreas_ANALYSIS", force_2d=True)
    g = g.to_crs(26915)
    simple = g.geometry.simplify(50, preserve_topology=True).iloc[0]
    layer = shapely.get_parts(simple)
    layer = layer[shapely.is_valid(layer)]
    parcels = ctx.parcels_valid
    tree = shapely.STRtree(layer)
    pi, li = tree.query(parcels, predicate="intersects")
    pieces = np.empty(len(pi), dtype=object)
    for start in range(0, len(pi), 50000):
        stop = start + 50000
        pieces[start:stop] = shapely.intersection(parcels[pi[start:stop]], layer[li[start:stop]])
    keep = ~shapely.is_empty(pieces)
    pieces, areas = pieces[keep], shapely.area(pieces[keep])
    # the notebook's second step: every piece touching a parcel counts toward that parcel
    jp, jq = shapely.STRtree(pieces).query(parcels, predicate="intersects")
    summed = pd.Series(areas[jq]).groupby(jp).sum().reindex(range(len(parcels)), fill_value=0.0)
    ratio = summed.to_numpy() / denominator
    return pd.DataFrame({"SB_repro": ratio, "SB_stored": np.asarray(stored_sb)})
