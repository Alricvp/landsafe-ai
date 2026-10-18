import numpy as np

from src import config
from src.features.build import build_features, feature_names
from tests.helpers import cohort


def test_cohort_shape_and_flare_rate():
    df, truths = cohort()
    assert df.patient_id.nunique() == config.N_PATIENTS
    assert len(df) == config.N_PATIENTS * config.N_DAYS
    assert 0.08 < df.flare.mean() < 0.18
    assert set(truths) == set(df.patient_id)


def test_meds_missed_always_has_planted_trigger():
    _, truths = cohort()
    assert all("meds_missed" in t for t in truths.values())


def test_features_have_no_missing_values_and_expected_columns():
    df, _ = cohort()
    f = build_features(df)
    assert not f[feature_names() + ["target"]].isna().any().any()
    assert set(f.target.unique()) <= {0, 1}


def test_lag_features_are_shifted_correctly():
    df, _ = cohort()
    pid = df.patient_id.iloc[0]
    d = df[df.patient_id == pid].reset_index(drop=True)
    f = build_features(d, with_target=False)
    row = f.iloc[10]
    t = d.index[d.day == row.day][0]
    assert row["dairy_servings_lag2"] == d.loc[t - 2, "dairy_servings"]
    assert row["symptom_score_lag1"] == d.loc[t - 1, "symptom_score"]


def test_target_looks_only_at_future_days():
    df, _ = cohort()
    pid = df.patient_id.iloc[0]
    d = df[df.patient_id == pid].reset_index(drop=True)
    f = build_features(d, horizon=7)
    row = f.iloc[20]
    t = d.index[d.day == row.day][0]
    expected = int(d.loc[t + 1:t + 7, "flare"].max())  # excludes today
    assert row["target"] == expected


def test_last_days_without_full_future_window_are_dropped():
    df, _ = cohort()
    d = df[df.patient_id == df.patient_id.iloc[0]]
    f = build_features(d, horizon=7)
    assert f.day.max() == d.day.max() - np.timedelta64(7, "D")
