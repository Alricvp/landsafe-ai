"""Personal trigger detection: lag-adjusted regression (Granger-style causal discovery).

For one patient we regress today's symptom score on
    * yesterday's symptom score            (adjusts for the disease's own persistence)
    * every candidate exposure at lags 1..L (exposures strictly BEFORE the outcome)
and test each exposure with a joint Wald test over its lags (heteroskedasticity-robust).
P-values are corrected across exposures with Benjamini-Hochberg.

Honest framing: this is temporal-precedence + adjustment, i.e. evidence of a trigger,
not a randomized proof. It is validated against planted triggers in tests/.
"""
import numpy as np
import pandas as pd
from scipy import stats

from src.config import EXPOSURES, LABELS, UNITS
from src.features.build import prepare


def _ols_hc1(X, y):
    n, k = X.shape
    xtx_inv = np.linalg.pinv(X.T @ X)
    beta = xtx_inv @ X.T @ y
    resid = y - X @ beta
    meat = X.T @ (X * (resid ** 2)[:, None])
    cov = xtx_inv @ meat @ xtx_inv * (n / max(n - k, 1))
    return beta, cov


def _benjamini_hochberg(pvals):
    p = np.asarray(pvals, dtype=float)
    order = np.argsort(p)
    ranked = p[order] * len(p) / (np.arange(len(p)) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    q = np.empty_like(p)
    q[order] = np.clip(ranked, 0, 1)
    return q


def detect_triggers(patient_df, max_lag=4, outcome="symptom_score", alpha=0.05, min_days=60):
    d = prepare(patient_df).reset_index(drop=True)
    if len(d) < min_days:
        raise ValueError(f"Need at least {min_days} days of logs to find triggers (got {len(d)}).")

    cols = {"ar1": d[outcome].shift(1)}
    for e in EXPOSURES:
        for k in range(1, max_lag + 1):
            cols[f"{e}__{k}"] = d[e].shift(k)
    X = pd.DataFrame(cols)
    ok = X.notna().all(axis=1)
    Xm = np.column_stack([np.ones(ok.sum()), X[ok].to_numpy(dtype=float)])
    y = d.loc[ok, outcome].to_numpy(dtype=float)
    beta, cov = _ols_hc1(Xm, y)
    names = ["const"] + list(X.columns)
    index = {n: i for i, n in enumerate(names)}

    rows = []
    for e in EXPOSURES:
        idx = [index[f"{e}__{k}"] for k in range(1, max_lag + 1)]
        b = beta[idx]
        V = cov[np.ix_(idx, idx)]
        wald = float(b @ np.linalg.pinv(V) @ b)
        p = float(stats.chi2.sf(wald, df=len(idx)))
        se = np.sqrt(np.clip(np.diag(V), 0, None))
        tvals = np.divide(b, se, out=np.zeros_like(b), where=se > 0)
        best = int(np.argmax(np.abs(tvals)))
        rows.append({
            "factor": e,
            "label": LABELS[e],
            "unit": UNITS[e],
            "best_lag_days": best + 1,
            "effect": float(b[best]),
            "ci_low": float(b[best] - 1.96 * se[best]),
            "ci_high": float(b[best] + 1.96 * se[best]),
            "p_value": p,
        })

    q = _benjamini_hochberg([r["p_value"] for r in rows])
    for r, qv in zip(rows, q):
        r["q_value"] = float(qv)
        r["is_trigger"] = bool(qv < alpha and r["effect"] > 0)
        r["summary"] = _summary(r)
    rows.sort(key=lambda r: r["p_value"])
    return rows


def _summary(r):
    if not r["is_trigger"]:
        return f"No clear link between {r['label'].lower()} and later symptoms."
    day = "day" if r["best_lag_days"] == 1 else "days"
    return (f"{r['label']}: symptoms tend to rise about {r['best_lag_days']} {day} later "
            f"(+{r['effect']:.2f} points {r['unit']}).")


def score_against_truth(found, truth):
    """Precision / recall of detected triggers vs planted ones (for demos and tests)."""
    detected = {r["factor"] for r in found if r["is_trigger"]}
    planted = set(truth)
    tp = len(detected & planted)
    return {
        "detected": sorted(detected),
        "planted": sorted(planted),
        "true_positives": tp,
        "false_positives": len(detected - planted),
        "false_negatives": len(planted - detected),
    }
