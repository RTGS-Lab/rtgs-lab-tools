"""Adjacent to Quality Community per the Scoring Review tab (rows 20-21).

Row 20: replace MLCCS A or B communities with DNR Native Plant Communities; "Yes (1) / No (0)
Keep this scoring criteria with the new processed layers"; merge, dissolve, clip county + 1 mile,
Near analysis. Row 21: MBS sites, updated link. v1 (BL_2.2 cell 5-6) buffers 100 ft but never
assigns the buffer, so it scores parcels that intersect. Here: Yes when the parcel is within
100 ft of an NPC polygon or an MBS site of Moderate or higher significance (the 2020 filter,
registry MBS_sites.attribute_filter). Setting npc_only drops MBS.
"""

import numpy as np

from ..sheet_common import FT100, edge_distance, frame, read_public

CHANGE_ID = "qc_sheet"
INPUT = ("QC_S", "Adjacent to Quality Community (DNR NPC + MBS)", "HQ", 0.10, 1)


def build(ctx):
    npc = read_public("dnr_native_plant_communities")
    mbs = read_public("MBS_sites")
    mbs = mbs[mbs.biodiv_sig.isin(["Outstanding", "High", "Moderate"])]
    out = frame(ctx, QC_S_edge_npc_m=edge_distance(ctx, npc.geometry.to_numpy()),
                QC_S_edge_mbs_m=edge_distance(ctx, mbs.geometry.to_numpy()))
    out.attrs["features"] = {"npc": len(npc), "mbs_moderate_up": len(mbs)}
    return out


def apply(values, frames, setting):
    f = frames[CHANGE_ID]
    d = f.QC_S_edge_npc_m.to_numpy()
    if setting == "npc_mbs":
        d = np.minimum(d, f.QC_S_edge_mbs_m.to_numpy())
    elif setting != "npc_only":
        raise ValueError(setting)
    values["QC_S"] = (d < FT100).astype(float)
