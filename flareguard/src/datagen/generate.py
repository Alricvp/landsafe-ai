"""Synthetic IBD daily-log generator with PLANTED, known triggers.

Each patient has a hidden inflammation state z_t that is persistent (AR(1)) and
is pushed up by personal triggers at known lags. Symptoms and flares are derived
from z_t. Because we know the truth, the causal module can be scored against it.

    python -m src.datagen.generate
"""
import argparse
import json

import numpy as np
import pandas as pd

from src import config

# trigger -> {lag_in_days: effect_on_inflammation_per_unit}, probability a patient is sensitive
TRIGGERS = {
    "dairy_servings": {"lags": {2: 0.35}, "p_sensitive": 0.50},
    "alcohol_units": {"lags": {1: 0.30}, "p_sensitive": 0.45},
    "stress": {"lags": {1: 0.14}, "p_sensitive": 0.70},
    "sleep_deficit": {"lags": {1: 0.30}, "p_sensitive": 0.60},
    "meds_missed": {"lags": {2: 0.90, 3: 0.50}, "p_sensitive": 1.00},
    "nsaid": {"lags": {1: 1.00}, "p_sensitive": 0.35},
}
AR = 0.6
FLARE_QUANTILE = 0.88  # ~12% of days are flare days


def _simulate_patient(rng, n_days, weekend):
    adherence = rng.uniform(0.78, 0.98)
    dairy_rate = rng.uniform(0.5, 1.8)
    drink_rate = rng.uniform(0.3, 1.3)

    stress = np.empty(n_days)
    stress[0] = 4.0
    for t in range(1, n_days):
        stress[t] = 0.7 * stress[t - 1] + 1.2 + rng.normal(0, 1.3)
    stress = np.clip(stress, 0, 10)

    sleep_hours = np.clip(7.2 - 0.18 * (stress - 4) + rng.normal(0, 0.9, n_days), 3.5, 10)
    exposures = {
        "dairy_servings": rng.poisson(dairy_rate + 0.3 * weekend).astype(float),
        "alcohol_units": rng.poisson(0.2 + 0.9 * weekend * drink_rate).astype(float),
        "stress": stress,
        "sleep_deficit": np.clip(7 - sleep_hours, 0, None),
        "meds_missed": (rng.random(n_days) >= adherence).astype(float),
        "nsaid": (rng.random(n_days) < 0.04).astype(float),
    }

    truth, drive = {}, np.zeros(n_days)
    for name, spec in TRIGGERS.items():
        if rng.random() >= spec["p_sensitive"]:
            continue
        strength = float(rng.uniform(0.6, 1.4))
        truth[name] = {"lags": sorted(spec["lags"]), "strength": round(strength, 3)}
        for lag, w in spec["lags"].items():
            drive[lag:] += strength * w * exposures[name][:-lag]

    noise = rng.normal(0, 0.35, n_days)
    z = np.zeros(n_days)
    for t in range(1, n_days):
        z[t] = AR * z[t - 1] + drive[t] + noise[t]
    return exposures, sleep_hours, z, truth


def simulate_cohort(n_patients=None, n_days=None, seed=None):
    n_patients = n_patients or config.N_PATIENTS
    n_days = n_days or config.N_DAYS
    rng = np.random.default_rng(config.SEED if seed is None else seed)
    days = pd.date_range("2025-01-01", periods=n_days, freq="D")
    weekend = (days.dayofweek >= 5).astype(float)

    raw, truths = [], {}
    for i in range(n_patients):
        pid = f"P{i + 1:03d}"
        exposures, sleep_hours, z, truth = _simulate_patient(rng, n_days, weekend)
        raw.append((pid, exposures, sleep_hours, z))
        truths[pid] = truth

    all_z = np.concatenate([r[3] for r in raw])
    mu, sd = all_z.mean(), all_z.std()
    thr = np.quantile((all_z - mu) / sd, FLARE_QUANTILE)

    frames = []
    for pid, exposures, sleep_hours, z in raw:
        zn = (z - mu) / sd
        n = len(zn)
        blood_p = 1 / (1 + np.exp(-(1.8 * zn - 2.5)))
        frames.append(pd.DataFrame({
            "patient_id": pid,
            "day": days,
            "dairy_servings": exposures["dairy_servings"].astype(int),
            "alcohol_units": exposures["alcohol_units"].astype(int),
            "stress": exposures["stress"].round(1),
            "sleep_hours": sleep_hours.round(1),
            "meds_taken": (1 - exposures["meds_missed"]).astype(int),
            "nsaid": exposures["nsaid"].astype(int),
            "symptom_score": np.clip(3 + 1.6 * zn + rng.normal(0, 0.6, n), 0, 10).round(1),
            "pain": np.clip(np.round(2 + 1.5 * zn + rng.normal(0, 0.8, n)), 0, 10).astype(int),
            "stool_frequency": np.clip(np.round(2 + 1.1 * zn + rng.normal(0, 1.0, n)), 0, 15).astype(int),
            "blood_in_stool": (rng.random(n) < blood_p).astype(int),
            "flare": (zn > thr).astype(int),
        }))
    return pd.concat(frames, ignore_index=True), truths


def generate_and_save(n_patients=None, n_days=None, seed=None):
    df, truths = simulate_cohort(n_patients, n_days, seed)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.LOGS_PATH, index=False)
    config.TRUTH_PATH.write_text(json.dumps(truths, indent=2))
    return df, truths


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--patients", type=int, default=None)
    ap.add_argument("--days", type=int, default=None)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    df, _ = generate_and_save(a.patients, a.days, a.seed)
    print(f"Wrote {len(df):,} rows for {df.patient_id.nunique()} patients to {config.LOGS_PATH}")
    print(f"Flare-day rate: {df.flare.mean():.1%}")
