"""Model-agnostic explanations by occlusion.

A factor's contribution = risk now  -  risk if that factor's features were replaced by
their cohort average. Features are grouped by factor (all lags of "dairy" move together),
so the output reads "dairy is adding 9 points of risk" instead of "dairy_lag2 = 3".
Comparing two days gives "what changed since yesterday".
"""
import re

import pandas as pd

from src.config import LABELS


def factor_of(feature_name):
    return re.sub(r"_(lag\d+|mean7)$", "", feature_name)


def factor_groups(feature_names):
    groups = {}
    for n in feature_names:
        groups.setdefault(factor_of(n), []).append(n)
    return groups


def contributions(bundle, X):
    """Return (per-factor contribution DataFrame, base risk array) for the rows of X."""
    names, means, model = bundle["feature_names"], bundle["means"], bundle["model"]
    Xf = X[names].reset_index(drop=True)
    base = model.predict_proba(Xf)[:, 1]
    out = {}
    for factor, cols in factor_groups(names).items():
        Xm = Xf.copy()
        for c in cols:
            Xm[c] = means[c]
        out[factor] = base - model.predict_proba(Xm)[:, 1]
    return pd.DataFrame(out), base


def _label(f):
    return LABELS.get(f, f.replace("_", " ").title())


def explain_last_two_days(bundle, feats, top_k=5):
    """feats: feature rows for ONE patient, sorted by day (needs >= 2 rows)."""
    rows = feats.tail(2)
    contrib, base = contributions(bundle, rows)
    today = contrib.iloc[-1]
    drivers = [
        {"factor": f, "label": _label(f), "contribution": float(v)}
        for f, v in today.reindex(today.abs().sort_values(ascending=False).index).items()
    ][:top_k]
    changes = []
    if len(rows) == 2:
        delta = contrib.iloc[-1] - contrib.iloc[0]
        changes = [
            {"factor": f, "label": _label(f), "delta": float(v)}
            for f, v in delta.reindex(delta.abs().sort_values(ascending=False).index).items()
        ][:top_k]
    return float(base[-1]), drivers, changes
