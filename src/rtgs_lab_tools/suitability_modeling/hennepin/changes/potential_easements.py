"""Nearness to potential easement acquisition: in the 2019 scoring document at 15% of Spatial
Context, absent from v1 (BL_1.3 is a passthrough).

2 = within 100 ft, 1 = within 1/2 mile, 0 = neither. Edge distance, per the document. The only
candidate layer is Easement_Inquiries; its status values do not match the document's query, so the
setting `all_inquiries` uses all 29 features. ContactName holds landowner names and is never read.
"""

import numpy as np
import pandas as pd
import pyogrio

from .natural_spaces import nearest_distance

CHANGE_ID = "potential_easements"
INPUT = ("PEA_Value", "Nearness to Potential Easements", "SC", 0.15, 2)


def build(ctx):
    g = pyogrio.read_dataframe(ctx.delivered["easements_gdb"], layer="Easement_Inquiries",
                               columns=["AcquisStatus"], force_2d=True).to_crs(26915)
    return pd.DataFrame({"PEA_edge_m": nearest_distance(ctx.parcels.geometry, g.make_valid())})


def apply(values, frames, setting):
    if setting != "all_inquiries":
        raise ValueError(setting)
    d = frames[CHANGE_ID].PEA_edge_m.to_numpy()
    values["PEA_Value"] = np.select([d < 30.48, d < 804.67], [2, 1], 0)
