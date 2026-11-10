"""Wildlife and Plant Conservation layers added or updated by the Scoring Review tab.

Row 26 Wildlife Action Network, updated layer: rank 1-5 (Low .. High), 0 outside; highest rank
on the parcel. Row 27 Conservation Opportunity Areas: Yes (1) / No (0). Row 30 Rusty Patched
Bumble Bee High Potential Zone: High (2) / Low (1) / neither (0). Row 31 Important Bird Areas,
updated polygons: Yes (1) / No (0). "On the parcel" = overlap with positive area (v1 BL_4.2/4.3
used sjoin intersects).
"""

from ..sheet_common import frame, max_value_overlap, read_public

CHANGE_ID = "wildlife_sheet"
INPUTS = [
    ("WAN_S", "Wildlife Action Network rank (2026 layer)", "WP", 0.08, 5),
    ("COA_S", "Conservation Opportunity Area", "WP", 0.08, 1),
    ("RPBB_S", "Rusty Patched Bumble Bee potential zone", "WP", 0.08, 2),
    ("Bird_S", "Important Bird Area (current polygons)", "WP", 0.16, 1),
]
RPBB = {"High Potential Zone": 2.0, "Low Potential Zone": 1.0}


def build(ctx):
    wan = read_public("WAN")
    coa = read_public("conservation_opportunity_areas")
    rpbb = read_public("rpbb_high_potential_zones")
    iba = read_public("important_bird_areas_public")
    out = frame(
        ctx,
        WAN_S_rank=max_value_overlap(ctx, wan.geometry.to_numpy(), wan["rank"].astype(float)),
        COA_S_in=max_value_overlap(ctx, coa.geometry.to_numpy(), [1.0] * len(coa)),
        RPBB_S_zone=max_value_overlap(ctx, rpbb.geometry.to_numpy(),
                                      rpbb.Zone.map(RPBB).fillna(0.0)),
        Bird_S_in=max_value_overlap(ctx, iba.geometry.to_numpy(), [1.0] * len(iba)),
    )
    out.attrs["features"] = {"WAN": len(wan), "COA": len(coa), "RPBB": len(rpbb), "IBA": len(iba)}
    return out


def apply(values, frames, setting):
    if setting != "sheet":
        raise ValueError(setting)
    f = frames[CHANGE_ID]
    values["WAN_S"] = f.WAN_S_rank.to_numpy()
    values["COA_S"] = f.COA_S_in.to_numpy()
    values["RPBB_S"] = f.RPBB_S_zone.to_numpy()
    values["Bird_S"] = f.Bird_S_in.to_numpy()
