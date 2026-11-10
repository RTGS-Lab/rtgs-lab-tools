"""Category membership, within-category weights and divisors as the Scoring Review tab states them.

The setting lists every input of the model: field -> {cat, weight, div, fallback}. reweight()
replaces the input list, so v1 inputs not listed (Relative Size inside Size_Value, groundwater
recharge GW_Value, ...) leave the model. When a listed field has no values because its change
is off (a without__ variant), the fallback v1 field stands in with its own v1 divisor; with no
fallback the field is skipped. apply() changes no values.
"""

from ..spec import INPUTS as V1_INPUTS

CHANGE_ID = "sheet_weights"
V1_DIV = {f: div for f, _, _, _, div in V1_INPUTS}


def apply(values, frames, setting):
    return None


def reweight(values, inputs, setting):
    labels = {i[0]: i[1] for i in inputs}
    out, used = [], {}
    for field, spec in setting["inputs"].items():
        use, div = field, spec["div"]
        if field not in values.columns:
            fb = spec.get("fallback")
            if fb is None or fb not in values.columns:
                used[field] = None
                continue
            use, div = fb, V1_DIV.get(fb, spec["div"])
        used[field] = use
        out.append((use, labels.get(use, use), spec["cat"], float(spec["weight"]), float(div)))
    return out, used
