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


V1_WEIGHT = {f: w for f, _, _, w, _ in V1_INPUTS}


def reweight(values, inputs, setting):
    """Substitution keys (analysis variants, not V2): force_v1 = fields replaced by their v1
    counterpart (v1 value and v1 divisor, V2 weight; dropped when there is none);
    weights_from_v1 = every field takes its v1 counterpart's within weight (0 when new in V2);
    extra = inputs appended as given (e.g. GW_Value back in); weight_override = {field: w}."""
    labels = {i[0]: i[1] for i in inputs}
    out, used = [], {}
    force = set(setting.get("force_v1") or [])
    specs = dict(setting["inputs"])
    specs.update(setting.get("extra") or {})
    for field, spec in specs.items():
        use, div = field, spec["div"]
        weight = float(spec["weight"])
        if setting.get("weights_from_v1"):
            weight = V1_WEIGHT.get(spec.get("v1_field") or field, 0.0)
        weight = float((setting.get("weight_override") or {}).get(field, weight))
        if field in force:
            v1 = spec.get("v1_field")
            if not v1:
                used[field] = None
                continue
            use, div = v1, V1_DIV[v1]
            used[field] = use
            out.append((use, labels.get(use, use), spec["cat"], weight, float(div)))
            continue
        if weight == 0:
            used[field] = None
            continue
        if field not in values.columns:
            fb = spec.get("fallback")
            if fb is None or fb not in values.columns:
                used[field] = None
                continue
            use, div = fb, V1_DIV.get(fb, spec["div"])
        used[field] = use
        out.append((use, labels.get(use, use), spec["cat"], weight, float(div)))
    return out, used
