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
import yaml

from .context import CONFIG_DIR, file_date, load_config, load_context, load_table, resolve, sha256_path
from .spec import CATEGORIES
from .variants import compare, run_variant


def build_modules(config):
    """Each module named by a change entry, once. distance_method has no build of its own: it reads
    the edge distances natural_spaces and protected_areas already computed."""
    skip = {"distance_method", "sheet_weights"}
    names = [e["module"] for e in config["changes"].values() if e["module"] not in skip]
    if config.get("ranking"):
        names.append("exclusions")
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
        # a change that adds a sheet input runs with the sheet weights it needs (fallbacks fill
        # the other inputs with v1 values)
        deps = {d: config["changes"][d]["setting"] for d in e.get("needs") or []}
        out[f"only__{cid}"] = {**deps, cid: e["setting"]}
        if cid in v2:
            out[f"without__{cid}"] = {k: s for k, s in v2.items() if k != cid}
        else:
            out[f"plus__{cid}"] = {**v2, cid: e["setting"]}
        for i, alt in enumerate(e.get("alternatives") or []):
            out[f"alt{i + 1}__{cid}"] = {**v2, cid: alt}
    out.update(named_variants())
    return out


def named_variants():
    """config/variants/<name>.yaml: a frozen set of active settings, e.g. the a343a98 V2."""
    out = {}
    config = None
    for f in sorted((CONFIG_DIR / "variants").glob("*.yaml")):
        v = yaml.safe_load(f.read_text())
        active = dict(v.get("active") or {})
        if v.get("base") == "v2":  # substitution variant: V2 with named overrides
            config = config or load_config()
            base = recommended(config)
            for cid, setting in active.items():
                if setting is None:
                    base.pop(cid, None)
                else:
                    base[cid] = setting
            if v.get("weights_patch"):
                import copy
                w = copy.deepcopy(base["sheet_weights"])
                w.update(v["weights_patch"])
                base["sheet_weights"] = w
            active = base
        out[v["name"]] = active
    return out


def ranked(rank_overall, overall, excluded):
    """Rank among parcels not excluded (descending, ties min, Overall_Value at 4 decimals as v1);
    0 for excluded parcels, which keep their index score."""
    r = np.zeros(len(overall), dtype=np.int64)
    keep = ~excluded
    r[keep] = pd.Series(np.asarray(overall)[keep]).round(4).rank(
        ascending=False, method="min").astype(np.int64).to_numpy()
    return r


def public_inputs(config):
    """fetch.json of every public layer on disk: URL and sha256 of raw download and gpkg."""
    root = Path(config.get("public_root", ""))
    out = {}
    for f in sorted(root.glob("*/fetch.json")):
        m = json.loads(f.read_text())
        out[m["key"]] = {k: m.get(k) for k in ("service_url", "download_url", "raw_sha256", "gpkg",
                                                "gpkg_sha256", "features", "finished")}
        for k, v in m.items():
            if isinstance(v, dict) and "gpkg_sha256" in v:
                out[f"{m['key']}_{k}"] = v
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
    linked = {}
    for p in sorted((out / "intermediate").glob("*.parquet")):
        if p.is_symlink():
            linked[p.stem] = {"target": str(p.resolve()), "sha256": sha256_path(p.resolve())}
    return {"commit": sha, "dirty": dirty, "python": platform.python_version(),
            "run_at": time.strftime("%F %T"), "inputs": entries,
            "public_layers": public_inputs(config), "intermediates_linked": linked}


def variants(out):
    config = load_config()
    table = load_table(config)
    frames = {p.stem: pd.read_parquet(p) for p in (out / "intermediate").glob("*.parquet")}
    for name, f in frames.items():
        if "PID" in f and not (f.PID.to_numpy() == table.PID.to_numpy()).all():
            raise ValueError(f"{name}: parcel order differs from v1")
    cols = [c for _, _, _, c in CATEGORIES] + ["Overall_Value", "Rank"]
    results, scaling, active_by_name = {}, {}, {}
    excluded, masks = None, {}
    if config.get("ranking") and "exclusions" in frames:
        from .changes.exclusions import masks as exclusion_masks
        prot, air = exclusion_masks(frames["exclusions"], config["ranking"])
        excluded = prot | air
        masks = {"protected": int(prot.sum()), "airport": int(air.sum()),
                 "both": int((prot & air).sum()), "ranked": int((~excluded).sum())}
        cols = cols + ["Rank_ranked"]
    for name, active in variant_list(config).items():
        results[name], scaling[name] = run_variant(table, frames, active, config)
        if excluded is not None:
            results[name]["Rank_ranked"] = ranked(results[name]["Rank"], results[name]["Overall_Value"],
                                                  excluded)
        active_by_name[name] = active
    (out / "variants").mkdir(exist_ok=True)
    for name in ["v1", "v2"] + [n for n in named_variants() if not n.startswith("sub_")]:
        res = results[name].copy()
        res.insert(0, "PID", table.PID.to_numpy())
        if excluded is not None:
            res["excluded_protected"], res["excluded_airport"] = prot, air
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
            "breaks": breaks, "config": config, "exclusions": masks}
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
