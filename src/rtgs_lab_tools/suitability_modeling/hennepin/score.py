"""Tier-2 values -> category scores -> Overall_Value -> Rank.

Overall_Value = 100 x sum(category weight x category score), where a category score is the
county-wide min-max of the sum of (within weight x value / divisor). Rank is descending, ties
share the lowest rank (method="min"), on Overall_Value rounded to 4 decimals as v1 stores it.
"""

import numpy as np
import pandas as pd

from .spec import CATEGORIES, CATEGORY_COLUMNS, CATEGORY_WEIGHTS


def _minmax(s):
    lo, hi = float(s.min()), float(s.max())
    if hi == lo:
        raise ValueError(f"category has no spread: {lo}")
    return (s - lo) / (hi - lo), lo, hi


def score(values, inputs):
    """values: DataFrame with one column per input field. inputs: list of input tuples.

    Returns (result, scaling). result holds tier-2 values, per-input points, raw and scaled
    category scores, Overall_Value, Rank. scaling records each category's raw min and max, which
    any hand calculation needs.
    """
    out = values[[i[0] for i in inputs]].copy()
    scaling = {}
    for key, _, weight, _ in CATEGORIES:
        members = [i for i in inputs if i[2] == key]
        terms = {f: within * values[f] / divisor for f, _, _, within, divisor in members}
        raw = sum(terms.values())
        scaled, lo, hi = _minmax(raw)
        scaling[key] = {"raw_min": lo, "raw_max": hi, "weight": weight}
        out[f"raw_{key}"] = raw
        out[CATEGORY_COLUMNS[key]] = scaled
        # A term's points: its share of the category's scaled score, in Overall_Value units.
        for f, term in terms.items():
            out[f"pts_{f}"] = 100 * weight * (term - (lo if len(terms) == 1 else 0)) / (hi - lo)
        if len(terms) > 1 and lo != 0:
            raise ValueError(f"{key}: raw minimum {lo} is not 0, points would not add up")
    overall = 100 * sum(CATEGORY_WEIGHTS[k] * out[CATEGORY_COLUMNS[k]] for k in CATEGORY_WEIGHTS)
    out["Overall_Value"] = overall
    out["Rank"] = overall.round(4).rank(ascending=False, method="min").astype(np.int64)
    return out, scaling


def v1_stored_columns():
    return [c[3] for c in CATEGORIES] + ["Overall_Value", "Rank"]


def agreement(a, b):
    """Rank agreement between two runs on the same parcel order (Series of ranks and scores)."""
    return {
        "spearman": float(pd.Series(a).rank().corr(pd.Series(b).rank())),
        "identical_rank_share": float((np.asarray(a) == np.asarray(b)).mean()),
    }
