"""Apply a set of change settings to v1's tier-2 values, then score."""

import importlib

import numpy as np
import pandas as pd

from .score import score
from .spec import INPUTS

_MODULES = {}


def _module(name):
    if name not in _MODULES:
        _MODULES[name] = importlib.import_module(f"{__package__}.changes.{name}")
    return _MODULES[name]


def apply_changes(table, frames, active, config):
    """active: {change_id: setting}. Returns (tier-2 values, input list)."""
    values = table[[i[0] for i in INPUTS]].copy()
    inputs = list(INPUTS)
    entries = config["changes"]
    edge = "edge_distance" in active
    sources = []
    ns_setting = None
    weights = None
    for cid, setting in active.items():
        module = entries[cid]["module"]
        if module == "sheet_weights":
            weights = setting
        elif module == "protected_areas":
            sources.append(setting["source"])
        elif module == "distance_method":
            pass
        elif module == "natural_spaces":
            ns_setting = setting
        else:
            mod = _module(module)
            mod.apply(values, frames, setting)
            if hasattr(mod, "INPUT"):
                inputs.append(mod.INPUT)
            inputs.extend(getattr(mod, "INPUTS", []))
    if sources or edge:
        _module("protected_areas").apply(values, frames, {"sources": sources, "method": "edge" if edge else "part_centroid"})
    if ns_setting or edge:
        _module("natural_spaces").apply(values, frames, "edge" if edge else ns_setting)
    if weights is not None:
        # Scoring Review V2: the input list and its weights come from config, not spec.INPUTS
        inputs, used = _module("sheet_weights").reweight(values, inputs, weights)
        values.attrs["weights_used"] = used
    return values, inputs


def run_variant(table, frames, active, config):
    values, inputs = apply_changes(table, frames, active, config)
    return score(values, inputs)


def compare(ref, other):
    """ref and other are score() results on the same parcel order."""
    a, b = ref["Rank"].to_numpy(), other["Rank"].to_numpy()
    shift = np.abs(a - b)
    delta = other["Overall_Value"].to_numpy() - ref["Overall_Value"].to_numpy()
    out = {
        "spearman": float(pd.Series(a).rank().corr(pd.Series(b).rank())),
        "median_abs_rank_shift": float(np.median(shift)),
        "p95_abs_rank_shift": float(np.percentile(shift, 95)),
        "max_abs_rank_shift": int(shift.max()),
        "median_overall_change": float(np.median(delta)),
        "max_abs_overall_change": float(np.abs(delta).max()),
        "parcels_score_changed": int((np.abs(delta) > 1e-6).sum()),
    }
    for k in (100, 1000, 10000):
        out[f"top{k}_kept"] = int(len(np.intersect1d(np.argsort(a, kind="stable")[:k],
                                                     np.argsort(b, kind="stable")[:k])))
    return out
