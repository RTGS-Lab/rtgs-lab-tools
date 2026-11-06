"""Build intermediates, run v1, V2 and the one-change variants, and write the manifest.

python -m rtgs_lab_tools.suitability_modeling.hennepin.run build --out DIR [--only id ...]
python -m rtgs_lab_tools.suitability_modeling.hennepin.run variants --out DIR
"""

import argparse
import importlib
import json
import platform
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .breaks import natural_breaks
from .context import file_date, load_config, load_context, load_table, resolve, sha256_path
from .spec import CATEGORIES
from .variants import compare, run_variant


def build_modules(config):
    """Each module named by a change entry, once. distance_method has no build of its own: it reads
    the edge distances natural_spaces and protected_areas already computed."""
    names = [e["module"] for e in config["changes"].values() if e["module"] != "distance_method"]
    return list(dict.fromkeys(names))


def commit():
    here = Path(__file__).parent
    sha = subprocess.run(["git", "-C", str(here), "rev-parse", "HEAD"], capture_output=True,
                         text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(here), "status", "--porcelain", "."],
                           capture_output=True, text=True).stdout.strip()
    return sha, bool(dirty)


def build(out, only):
    config = load_config()
    ctx = load_context(config, out)
    (out / "intermediate").mkdir(parents=True, exist_ok=True)
    for name in only or build_modules(config):
        start = time.time()
        mod = importlib.import_module(f"{__package__}.changes.{name}")
        frame = mod.build(ctx)
        attrs = dict(frame.attrs)
        frame.attrs = {}
        if len(frame) == len(ctx.parcels):
            frame.insert(0, "PID", ctx.parcels.PID.to_numpy())
        frame.to_parquet(out / "intermediate" / f"{name}.parquet")
        record = {"module": name, "rows": len(frame), "seconds": round(time.time() - start, 1),
                  "attrs": attrs, "commit": commit()[0], "built": time.strftime("%F %T")}
        (out / "intermediate" / f"{name}.json").write_text(json.dumps(record, indent=1))
        print(name, record["rows"], record["seconds"], flush=True)


def recommended(config):
    return {c: e["setting"] for c, e in config["changes"].items() if e["enabled"]}


def variant_list(config):
    """name -> (reference run, active settings). Every enabled and disabled entry is tried alone
    against v1, every enabled entry is removed once from V2, and each listed alternative setting
    replaces the V2 setting once."""
    v2 = recommended(config)
    out = {"v1": {}, "v2": v2}
    for cid, e in config["changes"].items():
        out[f"only__{cid}"] = {cid: e["setting"]}
        if cid in v2:
            out[f"without__{cid}"] = {k: s for k, s in v2.items() if k != cid}
        else:
            out[f"plus__{cid}"] = {**v2, cid: e["setting"]}
        for i, alt in enumerate(e.get("alternatives") or []):
            out[f"alt{i + 1}__{cid}"] = {**v2, cid: alt}
    return out


def class_counts(values, uppers):
    cls = np.searchsorted(np.asarray(uppers), np.asarray(values), side="left")
    return np.clip(cls, 0, len(uppers) - 1)


def manifest(out, config):
    entries = {}
    for name in ("v1_csv", "v1_shp", "gdb", "county"):
        p = config["paths"][name]
        entries[name] = {"path": p, "sha256": sha256_path(p), "date": file_date(p)}
    for name, p in config["delivered_zips"].items():
        p = resolve(p, out)
        entries[name] = {"path": p, "sha256": sha256_path(p), "date": file_date(p)}
    sha, dirty = commit()
    return {"commit": sha, "dirty": dirty, "python": platform.python_version(),
            "run_at": time.strftime("%F %T"), "inputs": entries}


def variants(out):
    config = load_config()
    table = load_table(config)
    frames = {p.stem: pd.read_parquet(p) for p in (out / "intermediate").glob("*.parquet")}
    for name, f in frames.items():
        if "PID" in f and not (f.PID.to_numpy() == table.PID.to_numpy()).all():
            raise ValueError(f"{name}: parcel order differs from v1")
    cols = [c for _, _, _, c in CATEGORIES] + ["Overall_Value", "Rank"]
    results, scaling, active_by_name = {}, {}, {}
    for name, active in variant_list(config).items():
        results[name], scaling[name] = run_variant(table, frames, active, config)
        active_by_name[name] = active
    (out / "variants").mkdir(exist_ok=True)
    for name in ("v1", "v2"):
        res = results[name].copy()
        res.insert(0, "PID", table.PID.to_numpy())
        res.to_parquet(out / "variants" / f"{name}_full.parquet")
    rows = []
    for name, res in results.items():
        pd.DataFrame({"PID": table.PID.to_numpy(), **{c: res[c].to_numpy() for c in cols}}).to_parquet(
            out / "variants" / f"{name}.parquet")
        rows.append({"variant": name, "ref": "v1", **compare(results["v1"], res)})
        rows.append({"variant": name, "ref": "v2", **compare(results["v2"], res)})
    pd.DataFrame(rows).to_json(out / "variant_effects.jsonl", orient="records", lines=True)
    breaks = {n: natural_breaks(results[n]["Overall_Value"]) for n in ("v1", "v2")}
    meta = {"manifest": manifest(out, config), "scaling": scaling, "active": active_by_name,
            "breaks": breaks, "config": config}
    (out / "run_meta.json").write_text(json.dumps(meta, indent=1, default=str))
    print("variants", len(results), "breaks", breaks, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["build", "variants"])
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    if a.step == "build":
        build(a.out, a.only)
    else:
        variants(a.out)


if __name__ == "__main__":
    main()
