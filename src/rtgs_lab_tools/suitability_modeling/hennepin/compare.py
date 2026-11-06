"""v1 against V2: rank shifts, largest movers and why, category changes, class changes, by city.

python -m rtgs_lab_tools.suitability_modeling.hennepin.compare --out DIR --parcel-table CSV.gz
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .run import class_counts
from .spec import CATEGORIES, INPUTS

ALL_FIELDS = [i[0] for i in INPUTS] + ["NHIS_Value"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--parcel-table", type=Path)
    a = ap.parse_args()
    out = a.out
    cmp_dir = out / "compare"
    cmp_dir.mkdir(exist_ok=True)
    meta = json.loads((out / "run_meta.json").read_text())
    v1 = pd.read_parquet(out / "variants" / "v1_full.parquet")
    v2 = pd.read_parquet(out / "variants" / "v2_full.parquet")
    t = pd.DataFrame({"PID": v1.PID, "Overall_v1": v1.Overall_Value, "Overall_v2": v2.Overall_Value,
                      "Rank_v1": v1.Rank, "Rank_v2": v2.Rank})
    t["rank_gain"] = t.Rank_v1 - t.Rank_v2
    t["overall_change"] = t.Overall_v2 - t.Overall_v1
    for f in ALL_FIELDS:
        old = v1[f"pts_{f}"] if f"pts_{f}" in v1 else 0.0
        t[f"dpts_{f}"] = v2[f"pts_{f}"] - old
    for _, _, _, col in CATEGORIES:
        t[f"d_{col}"] = v2[col] - v1[col]
    t["class_v1"] = class_counts(t.Overall_v1, meta["breaks"]["v1"]) + 1
    t["class_v2"] = class_counts(t.Overall_v2, meta["breaks"]["v2"]) + 1
    if a.parcel_table:
        m = pd.read_csv(a.parcel_table, dtype={"PID": str}, usecols=["PID", "MUNIC_NM", "acres"])
        t = t.merge(m, on="PID", how="left")
    t.to_parquet(cmp_dir / "parcel_changes.parquet")

    dp = [f"dpts_{f}" for f in ALL_FIELDS]
    t["main_driver"] = t[dp].abs().idxmax(axis=1).str.replace("dpts_", "").str.replace("_Value", "")
    movers = pd.concat([t.nlargest(25, "rank_gain").assign(direction="up"),
                        t.nsmallest(25, "rank_gain").assign(direction="down")])
    keep = ["direction", "PID", "MUNIC_NM", "acres", "Rank_v1", "Rank_v2", "rank_gain", "Overall_v1",
            "Overall_v2", "main_driver"] + dp
    movers[[c for c in keep if c in movers]].to_csv(cmp_dir / "largest_movers.tsv", sep="\t", index=False)
    top = t[(t.Rank_v1 <= 1000) | (t.Rank_v2 <= 1000)]
    top_up = top.nlargest(25, "rank_gain").assign(direction="up")
    top_down = top.nsmallest(25, "rank_gain").assign(direction="down")
    pd.concat([top_up, top_down])[[c for c in keep if c in top]].to_csv(
        cmp_dir / "largest_movers_top1000.tsv", sep="\t", index=False)
    summary = {
        "rank_gain_percentiles": {str(q): float(t.rank_gain.quantile(q / 100))
                                  for q in (1, 5, 25, 50, 75, 95, 99)},
        "abs_rank_shift_median": float(t.rank_gain.abs().median()),
        "overall_v1": t.Overall_v1.describe().to_dict(),
        "overall_v2": t.Overall_v2.describe().to_dict(),
        "main_driver_counts": t.main_driver.value_counts().to_dict(),
        "category_change": {},
        "input_points_change_abs_mean": {f: float(t[f"dpts_{f}"].abs().mean()) for f in ALL_FIELDS},
    }
    for _, label, w, col in CATEGORIES:
        d = t[f"d_{col}"]
        summary["category_change"][label] = {
            "weight": w, "mean_v1": float(v1[col].mean()), "mean_v2": float(v2[col].mean()),
            "median_v1": float(v1[col].median()), "median_v2": float(v2[col].median()),
            "parcels_changed": int((d.abs() > 1e-9).sum()), "mean_abs_change": float(d.abs().mean())}
    (cmp_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    pd.crosstab(t.class_v1, t.class_v2).to_csv(cmp_dir / "class_transition.tsv", sep="\t")
    if "MUNIC_NM" in t:
        g = t.groupby("MUNIC_NM").agg(parcels=("PID", "size"), acres=("acres", "sum"),
                                      median_rank_v1=("Rank_v1", "median"),
                                      median_rank_v2=("Rank_v2", "median"),
                                      top1000_v1=("Rank_v1", lambda s: int((s <= 1000).sum())),
                                      top1000_v2=("Rank_v2", lambda s: int((s <= 1000).sum())))
        g.to_csv(cmp_dir / "by_city.tsv", sep="\t")
    print(json.dumps({k: summary[k] for k in ("rank_gain_percentiles", "main_driver_counts")}, indent=1))


if __name__ == "__main__":
    main()
