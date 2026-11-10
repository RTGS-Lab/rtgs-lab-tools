"""Natural Spaces per the Scoring Review tab (rows 13-16): two new layers in place of MLCCS.

Row 13 (Ecologically Significant Areas, MLCCS) and row 14 (Priority Natural Resource Corridors)
are removed. Row 15 TNC Resilient and Connected Network: no public download of its classes
(registry tnc_resilient_lands.model_availability), so it is left out. Row 16 Metro Conservation
Corridors: clip county + 1 mile, Near analysis, 3 / 2 / 1 / 0 by 100 ft / 1/2 mile / 1 mile.
With one of the two layers available, NS_S is the MeCC score.
"""

from ..sheet_common import distance_points, edge_distance, frame, read_public

CHANGE_ID = "ns_sheet"
INPUT = ("NS_S", "Natural Spaces (Metro Conservation Corridors)", "SC", 0.35, 3)


def build(ctx):
    mecc = read_public("metro_conservation_corridors")
    out = frame(ctx, NS_S_edge_mecc_m=edge_distance(ctx, mecc.geometry.to_numpy()))
    out.attrs["features"] = {"metro_conservation_corridors": len(mecc)}
    return out


def apply(values, frames, setting):
    if setting != "mecc":
        raise ValueError(setting)
    values["NS_S"] = distance_points(frames[CHANGE_ID].NS_S_edge_mecc_m.to_numpy(), (3, 2, 1))
