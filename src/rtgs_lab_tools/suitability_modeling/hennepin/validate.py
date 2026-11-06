"""Validation of the v1 baseline and V2 run. Exit code 1 when any FAIL check fails.

python -m rtgs_lab_tools.suitability_modeling.hennepin.validate --out DIR --published JSONL
Writes validation.json and validation.txt. A check is PASS or FAIL against a stated test; REPORT
lines carry a number with no pass mark.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio
import shapely

from .breaks import natural_breaks
from .changes import natural_spaces
from .context import load_config, load_context, load_table, resolve
from .spec import CATEGORIES, CATEGORY_COLUMNS, INPUTS

HAND_PARCELS = 6


def load_context_paths(config, out):
    return {k: resolve(v, out) for k, v in config["delivered"].items()}


class Log:
    def __init__(self):
        self.rows = []

    def check(self, name, ok, detail):
        self.rows.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": str(detail)})

    def report(self, name, detail):
        self.rows.append({"check": name, "result": "REPORT", "detail": str(detail)})


def hand_calc(row, scaling, inputs):
    """Plain arithmetic from tier-2 values and each category's raw min and max."""
    total = 0.0
    for key, _, weight, _ in CATEGORIES:
        raw = sum(within * float(row[f]) / divisor for f, _, c, within, divisor in inputs if c == key)
        s = scaling[key]
        total += weight * (raw - s["raw_min"]) / (s["raw_max"] - s["raw_min"])
    return 100 * total


def validate_run(log, tag, full, scaling, inputs, expected_rows):
    log.check(f"{tag}: parcel count", len(full) == expected_rows, f"{len(full):,}")
    log.check(f"{tag}: no duplicate PID", not full.PID.duplicated().any(),
              int(full.PID.duplicated().sum()))
    nulls = full.isna().sum()
    log.check(f"{tag}: no null values", int(nulls.sum()) == 0, nulls[nulls > 0].to_dict())
    log.check(f"{tag}: category weights sum to 1", abs(sum(s["weight"] for s in scaling.values()) - 1) < 1e-12,
              {k: s["weight"] for k, s in scaling.items()})
    for key, label, _, col in CATEGORIES:
        lo, hi = float(full[col].min()), float(full[col].max())
        log.check(f"{tag}: {label} score spans 0 to 1", abs(lo) < 1e-9 and abs(hi - 1) < 1e-9,
                  f"{lo:.6f} to {hi:.6f}")
        log.report(f"{tag}: {label} within weights",
                   {i[0]: i[3] for i in inputs if i[2] == key})
    for f, *_ in inputs:
        s = full[f]
        log.report(f"{tag}: {f} range", f"{s.min():.6g} to {s.max():.6g}; zero share "
                                         f"{(s == 0).mean():.4f}")
    o = full.Overall_Value
    log.check(f"{tag}: Overall_Value inside 0 to 100", o.min() >= 0 and o.max() <= 100,
              f"{o.min():.4f} to {o.max():.4f}")
    points = full[[f"pts_{i[0]}" for i in inputs]].sum(axis=1)
    log.check(f"{tag}: input points add to Overall_Value", (points - o).abs().max() < 1e-8,
              f"max abs diff {(points - o).abs().max():.2e}")
    ordered = full.sort_values("Rank")
    log.check(f"{tag}: rank monotonic with score",
              bool((ordered.Overall_Value.round(4).diff().dropna() <= 0).all()),
              f"rank 1 score {ordered.Overall_Value.iloc[0]:.4f}, last {ordered.Overall_Value.iloc[-1]:.4f}")
    log.check(f"{tag}: rank equals descending min-rank of rounded score",
              bool((o.round(4).rank(ascending=False, method="min") == full.Rank).all()),
              f"max rank {full.Rank.max():,}")
    picks = pd.concat([ordered.head(1), ordered.iloc[[len(ordered) // 4, len(ordered) // 2]],
                       full.nlargest(1, "Size_Value"), full.nlargest(1, inputs[-1][0]),
                       ordered.tail(1)]).head(HAND_PARCELS)
    worst = max(abs(hand_calc(r, scaling, inputs) - r.Overall_Value) for _, r in picks.iterrows())
    log.check(f"{tag}: hand calculation on {len(picks)} parcels", worst < 1e-8,
              f"PIDs {picks.PID.tolist()}; max abs diff {worst:.2e}")
    return picks.PID.tolist()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--published", type=Path)
    ap.add_argument("--w43", type=Path, help="2026-W43 task dir with the 10/22 replay")
    ap.add_argument("--with-water-repro", action="store_true")
    a = ap.parse_args()
    out = a.out
    log = Log()
    config = load_config()
    table = load_table(config)
    meta = json.loads((out / "run_meta.json").read_text())
    v1 = pd.read_parquet(out / "variants" / "v1_full.parquet")
    v2 = pd.read_parquet(out / "variants" / "v2_full.parquet")
    frames = {p.stem: pd.read_parquet(p) for p in (out / "intermediate").glob("*.parquet")}

    # --- baseline
    diff = (v1.Overall_Value - table.Overall_Value).abs()
    log.check("baseline: recomputed Overall_Value equals v1 table (4 decimals)", diff.max() < 6e-5 + 1e-9,
              f"max abs diff {diff.max():.2e}")
    match = (v1.Rank.to_numpy() == table.Rank.to_numpy()).mean()
    log.check("baseline: recomputed rank equals v1 table", match == 1, f"match rate {match:.6f}")
    for _, _, _, col in CATEGORIES:
        d = (v1[col] - table[col]).abs().max()
        log.check(f"baseline: {col} equals v1 table", d < 1e-6, f"max abs diff {d:.2e}")
    if a.published and a.published.exists():
        pub = pd.read_json(a.published, lines=True, dtype={"PID": str})
        m = pub.merge(v1[["PID", "Overall_Value", "Rank"]], on="PID", how="left")
        rate = (m.Rank_x == m.Rank_y).mean()
        d = (m.Overall_Va - m.Overall_Value).abs().max()
        log.check("baseline: recomputed rank equals the published layer (sample)", rate == 1,
                  f"{len(pub):,} sampled parcels, match rate {rate:.6f}, score max abs diff {d:.2e}")
    if a.w43:
        rep = pd.read_parquet(next(a.w43.glob("24-working-*replay-results.parquet")),
                              columns=["suitability_score"])
        d = (rep.suitability_score.to_numpy() - v1.Overall_Value.to_numpy())
        log.check("baseline: equals the W43 run-config replay", np.abs(d).max() < 1e-3,
                  f"max abs diff {np.abs(d).max():.2e}")
        corr = pd.read_parquet(next(a.w43.glob("38-working-*corr-results.parquet")),
                               columns=["suitability_score"])
        only = pd.read_parquet(out / "variants" / "only__natural_spaces.parquet")
        d = np.abs(corr.suitability_score.to_numpy() - only.Overall_Value.to_numpy()).max()
        log.check("Natural Spaces fix equals the W43 corrected replay", d < 1e-3, f"max abs diff {d:.2e}")
    ns = frames["natural_spaces"]
    same = (natural_spaces.distance_class(ns.NS_dist_v1_point_m.to_numpy()) == table.NS_Value).mean()
    log.check("baseline: NS_Value reproduced from the v1 single point", same == 1, f"match {same:.6f}")
    pa = frames["protected_areas"]
    same = (natural_spaces.distance_class(pa.PA_dist_2020_m.to_numpy()) == table.PA_Value).mean()
    log.check("baseline: PA_Value reproduced from the 2020 layer", same == 1, f"match {same:.6f}")

    # --- runs
    v1_inputs = list(INPUTS)
    active = meta["active"]["v2"]
    v2_inputs = list(INPUTS) + ([("NHIS_Value", "NHIS", "WP", .30, 1)] if "nhis" in active else [])
    picks = {"v1": validate_run(log, "v1", v1, meta["scaling"]["v1"], v1_inputs, 445517),
             "v2": validate_run(log, "V2", v2, meta["scaling"]["v2"], v2_inputs, 445517)}

    # --- inputs
    w = frames["water_outlier"]
    for f in ("SB_share", "HCWI_share"):
        log.check(f"water: {f} is a share", w[f].between(0, 1).all(),
                  f"{w[f].min():.4f} to {w[f].max():.4f}")
    n = frames["nhis"]
    log.report("NHIS: parcels with no section overlap", int((n.NHIS_sections_crossed == 0).sum()))
    log.report("NHIS: parcels crossing more than one section", int((n.NHIS_sections_crossed > 1).sum()))
    log.report("NHIS: median share of parcel area in a section", float(n.NHIS_cover_share.median()))
    sections = pyogrio.read_dataframe(load_context_paths(config, out)["nhis_shp"], force_2d=True)
    pos = shapely.STRtree(sections.geometry.to_numpy())
    thirty_five = sections[sections.Polygon_Co == 35]
    touches = set(pos.query(thirty_five.geometry.to_numpy(), predicate="touches")[1])
    neighbours = sections.iloc[sorted(touches)]
    log.report("NHIS: Meaghan's example, adjacent sections scoring 0 and 35",
               f"Polygon_Co has {len(thirty_five)} section at 35, with "
               f"{int((neighbours.Polygon_Co == 0).sum())} of {len(neighbours)} touching sections at 0; "
               f"sum_Area_S maximum is {sections.sum_Area_S.max():.2f}, so it cannot hold a 35")
    r = frames["risk_of_development"]
    log.report("risk: v1 parcels found in Hockert file", f"{r.ROD_in_hockert.mean():.4f}")
    log.report("risk: v1 parcels at risk", int(r.ROD_at_risk.sum()))
    log.report("risk: at-risk parcels that are farm class", int((r.ROD_at_risk & r.ROD_farm).sum()))
    log.check("risk: every at-risk parcel has p_sub24", r.ROD_p_sub24[r.ROD_at_risk].notna().all(),
              int(r.ROD_p_sub24[r.ROD_at_risk].isna().sum()))
    bee = frames["bee_habitat"].iloc[0]
    log.check("bee: delivered layer equals the 2020 layer", bool(bee.classes_equal and bee.geometry_equal_within_1cm),
              bee.to_dict())

    # --- breaks
    ours = natural_breaks(v1.Overall_Value)
    published = [10.0705, 15.3075, 19.8327, 33.3379, 78.0392]
    log.report("breaks: our natural breaks on v1 vs published ArcGIS breaks",
               f"ours {[round(x, 2) for x in ours]}; published {published}")
    log.report("breaks: V2 natural breaks", [round(x, 2) for x in meta["breaks"]["v2"]])

    # --- engine
    for variant in ("v1", "v2"):
        f = out / "engine" / variant / "engine_check.json"
        if f.exists():
            e = json.loads(f.read_text())
            log.check(f"engine: run-config equals score.py, {variant}",
                      e["null_scores"] == 0 and e["parcels_over_0.0001"] == 0,
                      {k: e[k] for k in ("max_abs_diff", "parcels_over_0.0001", "identical_rank_share")})
        else:
            log.check(f"engine: run-config equals score.py, {variant}", False, "not run")

    # --- optional: the v1 SB cause
    if a.with_water_repro:
        from .changes.water_outlier import reproduce_v1
        ctx = load_context(config, out)
        rep = reproduce_v1(ctx, table.SB_Value, table.Shape_Area.to_numpy())
        rep.insert(0, "PID", table.PID.to_numpy())
        rep.to_parquet(out / "intermediate_water_v1_repro.parquet")
        close = np.isclose(rep.SB_repro, rep.SB_stored, rtol=1e-3, atol=1e-6)
        over = rep.SB_stored > 1
        log.report("water: BL_6.1 steps repeated, SB_Value within 0.1% of stored",
                   f"{close.mean():.4f} of all parcels; {close[over].mean():.4f} of parcels above 1; "
                   f"max repro {rep.SB_repro.max():,.0f}, stored max {rep.SB_stored.max():,.0f}")

    failed = [x for x in log.rows if x["result"] == "FAIL"]
    summary = {"passed": sum(x["result"] == "PASS" for x in log.rows), "failed": len(failed),
               "reported": sum(x["result"] == "REPORT" for x in log.rows), "hand_parcels": picks}
    (out / "validation.json").write_text(json.dumps({"summary": summary, "rows": log.rows}, indent=1))
    with open(out / "validation.txt", "w") as f:
        f.write(f"{summary}\n")
        for x in log.rows:
            f.write(f"{x['result']:<7}{x['check']}\n        {x['detail'][:400]}\n")
    print(summary)
    for x in failed:
        print("FAIL", x["check"], x["detail"][:300])
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
