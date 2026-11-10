"""Size per the Scoring Review tab (rows 23-24).

Row 23 Relative Size is removed ("This no longer is providing information"). Row 24 Absolute Size
is kept: > 80 acres (4), 50-79 (3), 30-49 (2), 10-29 (1), 5-9 (0.5), < 5 (0). The bins leave gaps
(79-80, 49-50, ...); lower bounds are taken as inclusive: [80, inf) 4, [50, 80) 3, [30, 50) 2,
[10, 30) 1, [5, 10) 0.5. Area is the v1 parcel Shape_Area (m2), the area v1 BL_3.1 bins on. v1
used four classes 3/2/1/0.5 at 79/49/29/9 acres plus relative size (BL_3.1 cells 3-5).
The "*Must be greater than 5 acres to consider" note is not applied (no rule for "very high").
"""

import numpy as np

from ..sheet_common import frame

CHANGE_ID = "size_sheet"
INPUT = ("SZ_S", "Absolute Size (acres, sheet bins)", "SZ", 1.00, 4)
ACRE_M2 = 4046.8564224


def build(ctx):
    return frame(ctx, SZ_S_acres=ctx.table.Shape_Area.to_numpy() / ACRE_M2)


def apply(values, frames, setting):
    if setting != "absolute_bins":
        raise ValueError(setting)
    a = frames[CHANGE_ID].SZ_S_acres.to_numpy()
    values["SZ_S"] = np.select([a >= 80, a >= 50, a >= 30, a >= 10, a >= 5], [4, 3, 2, 1, 0.5], 0.0)
