"""Turn raw daily logs into model features (lags, rolling windows, forward target)."""
import pandas as pd

from src import config
from src.config import EXPOSURES

EXPOSURE_LAGS = range(0, 4)
SYMPTOM_LAGS = range(0, 3)


def feature_names():
    names = [f"{e}_lag{k}" for e in EXPOSURES for k in EXPOSURE_LAGS]
    names += [f"symptom_score_lag{k}" for k in SYMPTOM_LAGS]
    names += ["symptom_score_mean7", "stress_mean7"]
    return names


def prepare(df):
    """Sort, parse dates and add the derived exposure columns."""
    d = df.copy()
    d["day"] = pd.to_datetime(d["day"])
    if "patient_id" not in d.columns:
        d["patient_id"] = "P000"
    d = d.sort_values(["patient_id", "day"]).reset_index(drop=True)
    d["sleep_deficit"] = (7 - d["sleep_hours"]).clip(lower=0)
    d["meds_missed"] = 1 - d["meds_taken"].astype(int)
    return d


def _forward_any(s, horizon):
    """1 if any flare occurs on days t+1 .. t+horizon (NaN if the window is incomplete)."""
    r = s.astype(float)[::-1]
    out = r.shift(1).rolling(horizon, min_periods=horizon).max()[::-1]
    return out.reindex(s.index)


def build_features(df, horizon=None, with_target=True):
    horizon = horizon or config.HORIZON_DAYS
    d = prepare(df)
    g = d.groupby("patient_id")
    cols = {}
    for e in EXPOSURES:
        for k in EXPOSURE_LAGS:
            cols[f"{e}_lag{k}"] = g[e].shift(k)
    for k in SYMPTOM_LAGS:
        cols[f"symptom_score_lag{k}"] = g["symptom_score"].shift(k)
    cols["symptom_score_mean7"] = g["symptom_score"].transform(lambda s: s.rolling(7, min_periods=7).mean())
    cols["stress_mean7"] = g["stress"].transform(lambda s: s.rolling(7, min_periods=7).mean())

    out = pd.concat([d[["patient_id", "day"]], pd.DataFrame(cols)], axis=1)
    required = feature_names()
    if with_target:
        out["target"] = g["flare"].transform(lambda s: _forward_any(s, horizon))
        required = required + ["target"]
    out = out.dropna(subset=required).reset_index(drop=True)
    if with_target:
        out["target"] = out["target"].astype(int)
    return out
