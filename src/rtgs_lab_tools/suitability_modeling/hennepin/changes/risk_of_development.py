"""Risk of development from Matthew Hockert's 2023 parcel model (thread:0000000000036c2e).

development_risk_parcels_2023.gpkg holds PIN (053-<13-digit PID>), at_risk and p_sub24, the chance
of subdivision in 2024. The 2019 scoring document scores 0 for developed or agriculture and 1/2/3
for the lowest/middle/highest third of risk. Setting `terciles_at_risk`: thirds of p_sub24 over all
at_risk PINs that join to a v1 parcel, 0 otherwise. Setting `terciles_no_farm` also scores USECLASS1
farm classes 0, as the document's "agriculture" reads. OWNER_NAME and other roll fields are not read.
"""

import numpy as np
import pandas as pd
import pyogrio

CHANGE_ID = "risk_of_development"


def build(ctx):
    h = pyogrio.read_dataframe(ctx.delivered["hockert_parcels_gpkg"], read_geometry=False,
                               columns=["PIN", "at_risk", "p_sub24", "USECLASS1"])
    h["PID"] = h.PIN.astype(str).str.replace(r"\D", "", regex=True).str[-13:]
    m = pd.DataFrame({"PID": ctx.parcels.PID.to_numpy()}).merge(h, on="PID", how="left")
    if len(m) != len(ctx.parcels):
        raise ValueError("PIN join changed the parcel count")
    return pd.DataFrame(
        {
            "ROD_in_hockert": m.PIN.notna().to_numpy(),
            "ROD_at_risk": (m.at_risk == 1).to_numpy(),
            "ROD_p_sub24": m.p_sub24.to_numpy(),
            "ROD_farm": m.USECLASS1.fillna("").str.contains("Farm", case=False).to_numpy(),
        }
    )


def terciles(p, at_risk):
    cut1, cut2 = np.quantile(p[at_risk], [1 / 3, 2 / 3])
    out = np.zeros(len(p))
    out[at_risk] = np.select([p[at_risk] > cut2, p[at_risk] > cut1], [3, 2], 1)
    return out, float(cut1), float(cut2)


def apply(values, frames, setting):
    f = frames[CHANGE_ID]
    at_risk = f.ROD_at_risk.to_numpy()
    if setting == "terciles_no_farm":
        at_risk = at_risk & ~f.ROD_farm.to_numpy()
    elif setting == "continuous":
        # Scoring Review row 35: "use continuous scoring based on the percentage of assigned risk
        # for each parcel. Will weight risk without bracketing." p_sub24 on at-risk parcels, else 0.
        p = np.nan_to_num(f.ROD_p_sub24.to_numpy(dtype=float), nan=0.0)
        values["ROD_Value"] = np.where(at_risk, p, 0.0)
        return
    elif setting != "terciles_at_risk":
        raise ValueError(setting)
    values["ROD_Value"] = terciles(f.ROD_p_sub24.to_numpy(), at_risk)[0]
