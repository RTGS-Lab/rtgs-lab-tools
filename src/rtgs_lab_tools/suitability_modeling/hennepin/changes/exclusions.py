"""Parcels scored but not ranked: already protected (Kristine) and airports (Scoring Review row 2).

Kristine, relayed by Bryan 2026-11-10: protected areas "get an index score, but are not apart of
the rank county wide". Protected = share of parcel area covered by the dissolved protected set
>= ranking.protected_share (0.5, the explorer's rule, nrpc-model-explorer data/build-data.py
PROTECTED_SHARE). Set: the Scoring Review sources in pa_sheet.SHEET_SOURCES. The explorer's set
(2020 composite + 2026 easements + Three Rivers gap + parks NR) is built too, for comparison.

Row 2 Proposed Layer Query: "make sure to remove the Airport parcels from this - they are oddly
not captured by any of these datasets and tend to rank highly". Airport = share of parcel area in
Met Council Generalized Land Use 2025 class Airport >= ranking.airport_share.
"""

import numpy as np
import shapely

from ..sheet_common import area_share, frame, read_public
from .pa_sheet import SHEET_SOURCES, sheet_layers

CHANGE_ID = "exclusions"
EXPLORER_SET = ["pa_2020", "easements_2026", "trpd_gap", "parks_nr"]


def _share(ctx, lay, names):
    geoms = np.concatenate([lay[n].to_numpy() for n in names])
    return area_share(ctx, shapely.union_all(shapely.make_valid(geoms)))[1]


def build(ctx):
    lay = sheet_layers(ctx)
    lu = read_public("land_use_2025")
    desc = lu.Dscrpt2025.fillna("")
    air = lu[desc.str.contains("airport", case=False)]
    out = frame(
        ctx,
        prot_share_sheet=_share(ctx, lay, SHEET_SOURCES),
        prot_share_explorer=_share(ctx, lay, EXPLORER_SET),
        airport_share=area_share(ctx, shapely.union_all(shapely.make_valid(
            air.geometry.to_numpy())))[1] if len(air) else np.zeros(len(ctx.parcels)),
    )
    out.attrs["land_use_2025_classes"] = sorted(desc.unique().tolist())
    out.attrs["airport_polygons"] = int(len(air))
    return out


def masks(frame_, ranking):
    """-> (protected, airport) boolean arrays under the base.yaml ranking block."""
    prot = frame_[f"prot_share_{ranking.get('protected_set', 'sheet')}"].to_numpy() >= float(
        ranking["protected_share"])
    air = frame_.airport_share.to_numpy() >= float(ranking["airport_share"])
    return prot, air
