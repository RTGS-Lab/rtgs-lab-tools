"""Water Resources per the Scoring Review tab (rows 41-47).

Row 41-42 Shoreland Buffer Area: PWI watercourses buffered 300 ft, PWI basins 1,000 ft outside
the basin; merge, dissolve, area within the parcel, relative to the parcel (v1 water_outlier
fix: share of parcel area). Row 42: public-water wetlands (pwi_class W) are dropped from the
basins, as redundant with NWI. Row 41 MD Notes say "Use a 50-ft buffer": setting
shoreland="50ft" [NEEDS DECISION]; the default keeps the Proposed Layer Query distances.
Row 43 Floodplain: FEMA NFHL; 100-year (1% annual chance, FLD_ZONE A*) = 2, 500-year (0.2%
annual chance, ZONE_SUBTY) = 1, highest on the parcel.
Row 44 Wetland area: NWI in place of HCWI, every NWI type ("include everything", 9/21 sheet);
share of parcel area.
Row 45 Headwater Area: Yes (1) / No (0). The query CATCH_POS = HEADWATER runs on the 2020 Level 9
auto-catchments (Headwaters_ANALYSIS); the current DNR suite has no Level 9 layer and no
CATCH_POS. Setting headwaters="level08_no_upstream" uses Level 8 catchments with up_count = 0.
v1 BL_6.4 summed the parts intersected (0-6); the sheet says Yes/No.
Row 46 Groundwater recharge: removed. Row 47: Water Table Aquifer Vulnerability in place of
geological sensitivity, combined_vulnerabilityrating High 2 / Medium 1 / Low, Unrated 0 (the
labels' points on the sheet's old scale), highest on the parcel.
"""

import numpy as np
import pyogrio
import shapely

from ..sheet_common import area_share, frame, max_value_overlap, read_public

CHANGE_ID = "water_sheet"
INPUTS = [
    ("SB_S", "Shoreland buffer share (2026 PWI)", "WR", 0.15, 1),
    ("FP_S", "Floodplain (FEMA NFHL)", "WR", 0.20, 2),
    ("NWI_S", "Wetland share (NWI)", "WR", 0.20, 1),
    ("HW_S", "Headwater area (yes/no)", "WR", 0.15, 1),
    ("AQV_S", "Water table aquifer vulnerability", "WR", 0.30, 2),
]
FT = 0.3048
AQV = {"High": 2.0, "Medium": 1.0, "Low": 0.0, "Unrated": 0.0}


def shoreland(basins, courses, basin_ft, course_ft):
    b = shapely.union_all(shapely.make_valid(basins))
    ring = shapely.difference(shapely.buffer(b, basin_ft * FT), b)
    c = shapely.buffer(shapely.union_all(courses), course_ft * FT)
    return shapely.union_all([ring, c])


def floodplain_points(g):
    zone = g.FLD_ZONE.fillna("").str.upper()
    sub = g.ZONE_SUBTY.fillna("").str.upper()
    pts = np.where(zone.str.startswith("A") | zone.str.startswith("V"), 2.0,
                   np.where(sub.str.contains("0.2 PCT"), 1.0, 0.0))
    return pts


def build(ctx):
    basins = read_public("public_waters_basins_watercourses")
    basins = basins[basins.pwi_class != "W"]
    courses = read_public("public_waters_basins_watercourses", "_watercourses")
    sb_area, sb = area_share(ctx, shoreland(basins.geometry.to_numpy(),
                                            courses.geometry.to_numpy(), 1000, 300))
    sb50_area, sb50 = area_share(ctx, shoreland(basins.geometry.to_numpy(),
                                                courses.geometry.to_numpy(), 50, 50))
    fema = read_public("fema_nfhl_flood_hazard_zones")
    fp = max_value_overlap(ctx, fema.geometry.to_numpy(), floodplain_points(fema))
    nwi = read_public("nwi_wetlands")
    nwi_area, nwi_share = area_share(ctx, shapely.union_all(shapely.make_valid(
        nwi.geometry.to_numpy())))
    hw20 = pyogrio.read_dataframe(ctx.gdb, layer="Headwaters_ANALYSIS", force_2d=True).to_crs(26915)
    l8 = read_public("watersheds")
    l8 = l8[l8.up_count.fillna(-1).astype(float) == 0]
    aqv = read_public("water_table_aquifer_vulnerability")
    out = frame(
        ctx,
        SB_S_share=sb, SB_S_share_50ft=sb50, SB_S_area_m2=sb_area,
        FP_S_points=fp,
        NWI_S_share=nwi_share, NWI_S_area_m2=nwi_area,
        HW_S_gdb2020=max_value_overlap(ctx, hw20.geometry.to_numpy(), [1.0] * len(hw20)),
        HW_S_level08=max_value_overlap(ctx, l8.geometry.to_numpy(), [1.0] * len(l8)),
        AQV_S_points=max_value_overlap(ctx, aqv.geometry.to_numpy(),
                                       aqv.combined_vulnerabilityrating.map(AQV).fillna(0.0)),
    )
    out.attrs["features"] = {"pwi_basins_no_wetland": len(basins), "pwi_watercourses": len(courses),
                             "nfhl": len(fema), "nwi": len(nwi), "headwaters_2020": len(hw20),
                             "level08_no_upstream": len(l8), "aquifer_vulnerability": len(aqv)}
    return out


def apply(values, frames, setting):
    """setting: dict(shoreland=300_1000ft|50ft, headwaters=gdb2020|level08_no_upstream)."""
    f = frames[CHANGE_ID]
    values["SB_S"] = (f.SB_S_share_50ft if setting.get("shoreland") == "50ft"
                      else f.SB_S_share).to_numpy()
    values["FP_S"] = f.FP_S_points.to_numpy()
    values["NWI_S"] = f.NWI_S_share.to_numpy()
    values["HW_S"] = (f.HW_S_level08 if setting.get("headwaters") == "level08_no_upstream"
                      else f.HW_S_gdb2020).to_numpy()
    values["AQV_S"] = f.AQV_S_points.to_numpy()
