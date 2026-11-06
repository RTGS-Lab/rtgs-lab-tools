"""Run the model through the generic engine, `rtgs suitability run-config`.

The engine is a flat weighted sum of 0-10 criteria, so the category scaling and divisors stay in
score.py, and each criterion carries s = 10 x points / weight at the parcel's representative point,
the pattern of the 2026-10-22 v1 replay. A match shows the engine's sum equals score.py's.

python -m rtgs_lab_tools.suitability_modeling.hennepin.engine_replay --out DIR --variant v2
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import yaml

from .context import load_config
from .spec import CATEGORY_WEIGHTS, INPUTS
from .variants import apply_changes


def prepare(out, variant):
    config = load_config()
    meta = json.loads((out / "run_meta.json").read_text())
    active = meta["active"][variant]
    full = pd.read_parquet(out / "variants" / f"{variant}_full.parquet")
    geo = pyogrio.read_dataframe(config["paths"]["v1_shp"], columns=["PID"], force_2d=True)
    geo = geo.set_crs(26915, allow_override=True)
    if not (geo.PID.to_numpy() == full.PID.to_numpy()).all():
        raise ValueError("parcel order differs")
    run = out / "engine" / variant
    (run / "data").mkdir(parents=True, exist_ok=True)
    units = out / "engine" / "units.parquet"
    if not units.exists():
        geo[["PID", "geometry"]].to_parquet(units)
    points = geo.representative_point()
    inputs = list(INPUTS)
    extra = {"nhis": ("NHIS_Value", "Natural Heritage Information System Occurrence", "WP", .30, 1),
             "potential_easements": ("PEA_Value", "Nearness to Potential Easements", "SC", .15, 2)}
    inputs += [spec for cid, spec in extra.items() if cid in active]
    criteria = []
    for field, label, cat, within, _ in inputs:
        total = sum(i[3] for i in inputs if i[2] == cat)
        weight = 100 * CATEGORY_WEIGHTS[cat] * within / total
        name = field.replace("_Value", "").lower()
        data = gpd.GeoDataFrame({"s": 10 * full[f"pts_{field}"].to_numpy() / weight},
                                geometry=points.to_numpy(), crs=26915)
        data.to_parquet(run / "data" / f"{name}.parquet")
        criteria.append({"dataset_name": name, "criterion_name": f"{label} ({field})",
                         "weight": round(weight, 10),
                         "scoring_function": {"type": "direct_value", "params": {"column": "s"},
                                              "output_range": [0, 10]}})
    criteria[-1]["weight"] = round(criteria[-1]["weight"] + 100
                                   - sum(c["weight"] for c in criteria), 10)
    model = {"model_id": f"hennepin_{variant}", "model_type": "weighted_overlay",
             "objective": f"Hennepin parcel prioritization, {variant}, pre-scaled criteria",
             "study_area": "Hennepin County",
             "analysis_units_config": {"type": "dataset", "max_cells": 500000},
             "criteria": criteria, "output_range": [0, 100]}
    (run / "model.yaml").write_text(yaml.safe_dump(model, sort_keys=False))
    cfg = {"study_area_path": config["paths"]["county"], "datasets_path": str(run / "data"),
           "analysis_units_path": str(units), "model_spec_path": str(run / "model.yaml"),
           "output_dir": str(run / "out"), "output_format": "geoparquet", "id_column": "PID"}
    (run / "config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    return run


def execute(run):
    code = ("from rtgs_lab_tools.suitability_modeling.cli import suitability_cli; "
            "suitability_cli()")
    subprocess.run([sys.executable, "-c", code, "run-config", "--config", str(run / "config.yaml")],
                   check=True)


def check(out, variant):
    run = out / "engine" / variant
    res = pd.read_parquet(next((run / "out").glob("*_results.parquet")),
                          columns=["PID", "suitability_score"])
    full = pd.read_parquet(out / "variants" / f"{variant}_full.parquet",
                           columns=["PID", "Overall_Value", "Rank"])
    m = full.merge(res, on="PID", how="left", validate="one_to_one")
    diff = (m.suitability_score - m.Overall_Value).abs()
    rank = m.suitability_score.round(4).rank(ascending=False, method="min")
    return {"variant": variant, "rows": int(len(m)), "null_scores": int(m.suitability_score.isna().sum()),
            "max_abs_diff": float(diff.max()), "parcels_over_0.0001": int((diff > 1e-4).sum()),
            "identical_rank_share": float((rank == m.Rank).mean()),
            "spearman": float(m.suitability_score.corr(m.Overall_Value, method="spearman"))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--variant", required=True)
    a = ap.parse_args()
    run = prepare(a.out, a.variant)
    execute(run)
    result = check(a.out, a.variant)
    (run / "engine_check.json").write_text(json.dumps(result, indent=1))
    print(result)


if __name__ == "__main__":
    main()
