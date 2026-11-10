"""New topic "Wildlife Important Waters" (Scoring Review rows 33-34).

Row 33 DNR Lakes of Biological Significance and row 34 Shallow Lakes Identified by DNR Wildlife,
each: dissolve, clip county + 1 mile, Near analysis, 3 within 100 ft / 2 within 1/2 mile /
1 within 1 mile / 0. The sheet gives the topic no weight.
"""

from ..sheet_common import distance_points, edge_distance, frame, read_public

CHANGE_ID = "important_waters"
INPUTS = [
    ("LBS_S", "Lakes of Biological Significance nearby", "WP", 0.11, 3),
    ("SHL_S", "DNR Wildlife shallow lakes nearby", "WP", 0.11, 3),
]


def build(ctx):
    lbs = read_public("lakes_of_biological_significance")
    shl = read_public("shallow_lakes_dnr_wildlife")
    out = frame(ctx, LBS_S_edge_m=edge_distance(ctx, lbs.geometry.to_numpy()),
                SHL_S_edge_m=edge_distance(ctx, shl.geometry.to_numpy()))
    out.attrs["features"] = {"lakes_of_biological_significance": len(lbs),
                             "shallow_lakes": len(shl)}
    return out


def apply(values, frames, setting):
    if setting != "distance_classes":
        raise ValueError(setting)
    f = frames[CHANGE_ID]
    values["LBS_S"] = distance_points(f.LBS_S_edge_m.to_numpy(), (3, 2, 1))
    values["SHL_S"] = distance_points(f.SHL_S_edge_m.to_numpy(), (3, 2, 1))
