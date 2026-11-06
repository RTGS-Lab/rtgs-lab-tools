"""Fast parcel/layer overlay helpers. No model logic here."""

import numpy as np
import pandas as pd
import shapely


def tile(geom, size=2000.0):
    """Cut a large polygon into grid tiles so that each parcel only meets a small piece."""
    xmin, ymin, xmax, ymax = geom.bounds
    pieces = []
    for x in np.arange(xmin, xmax, size):
        for y in np.arange(ymin, ymax, size):
            p = shapely.clip_by_rect(geom, x, y, x + size, y + size)
            if not p.is_empty:
                pieces.append(p)
    return np.array(pieces, dtype=object)


def polygons_only(geom):
    """Keep the polygonal part of a make_valid result."""
    parts = shapely.get_parts(geom)
    keep = parts[shapely.get_type_id(parts) == 3]
    return shapely.multipolygons(keep) if len(keep) else shapely.Polygon()


def overlap_areas(parcels, layer):
    """Long table of (parcel_index, layer_index, area) for every overlapping pair.

    parcels and layer are arrays of valid polygons. Layer pieces must not overlap each other when
    the caller sums the areas per parcel.
    """
    tree = shapely.STRtree(layer)
    pi, li = tree.query(parcels, predicate="intersects")
    areas = np.empty(len(pi))
    for start in range(0, len(pi), 50000):
        stop = start + 50000
        areas[start:stop] = shapely.area(shapely.intersection(parcels[pi[start:stop]],
                                                              layer[li[start:stop]]))
    return pd.DataFrame({"parcel": pi, "layer": li, "area": areas})
