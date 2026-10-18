from src.causal.triggers import detect_triggers, score_against_truth
from src.explain.local import explain_last_two_days
from src.features.build import build_features
from src.models.train import train_model
from tests.helpers import cohort


def test_model_beats_todays_symptoms_baseline_on_unseen_patients():
    df, _ = cohort()
    m = train_model(df)["metrics"]
    assert m["auc"] > 0.78
    assert m["auc"] > m["baseline_auc_todays_symptoms"]


def test_patient_split_has_no_overlap():
    df, _ = cohort()
    b = train_model(df)
    assert not set(b["train_patients"]) & set(b["test_patients"])


def test_explanations_cover_factors_and_changes():
    df, _ = cohort()
    b = train_model(df)
    pid = b["test_patients"][0]
    feats = build_features(df[df.patient_id == pid], with_target=False)
    risk, drivers, changes = explain_last_two_days(b, feats)
    assert 0 <= risk <= 1 and len(drivers) == 5 and len(changes) == 5
    assert all(set(d) == {"factor", "label", "contribution"} for d in drivers)


def test_causal_module_recovers_planted_triggers():
    df, truths = cohort()
    tp = fp = fn = lag_ok = lag_n = 0
    for pid in sorted(truths)[:15]:
        found = detect_triggers(df[df.patient_id == pid])
        s = score_against_truth(found, truths[pid])
        tp += s["true_positives"]; fp += s["false_positives"]; fn += s["false_negatives"]
        for r in found:
            if r["is_trigger"] and r["factor"] in truths[pid]:
                lag_n += 1
                lag_ok += r["best_lag_days"] in truths[pid][r["factor"]]["lags"]
    assert tp / (tp + fp) > 0.85
    assert tp / (tp + fn) > 0.80
    assert lag_ok / lag_n > 0.90


def test_too_little_history_is_rejected():
    df, _ = cohort()
    try:
        detect_triggers(df[df.patient_id == df.patient_id.iloc[0]].head(30))
    except ValueError:
        return
    raise AssertionError("expected ValueError")
