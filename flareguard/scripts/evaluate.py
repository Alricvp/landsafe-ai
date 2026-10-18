"""One-screen scorecard for the pitch: forecast quality + trigger recovery."""
import json

import pandas as pd

from src import config
from src.bootstrap import ensure_artifacts
from src.causal.triggers import detect_triggers, score_against_truth
from src.models.train import load_bundle

ensure_artifacts()
b = load_bundle()
m = b["metrics"]
print(f"Flare forecast ({b['horizon']}-day), {m['n_test_patients']} patients the model never saw")
print(f"  AUC                      {m['auc']:.3f}")
print(f"  AUC, today's symptoms    {m['baseline_auc_todays_symptoms']:.3f}   <- the naive baseline")
print(f"  Average precision        {m['average_precision']:.3f}  (base rate {m['base_rate']:.2f})")

df = pd.read_csv(config.LOGS_PATH)
truth = json.loads(config.TRUTH_PATH.read_text())
tp = fp = fn = lag_ok = lag_n = 0
for pid in sorted(df.patient_id.unique()):
    found = detect_triggers(df[df.patient_id == pid])
    s = score_against_truth(found, truth[pid])
    tp += s["true_positives"]; fp += s["false_positives"]; fn += s["false_negatives"]
    for r in found:
        if r["is_trigger"] and r["factor"] in truth[pid]:
            lag_n += 1
            lag_ok += r["best_lag_days"] in truth[pid][r["factor"]]["lags"]
print(f"\nTrigger detection vs planted truth, {df.patient_id.nunique()} patients")
print(f"  Precision {tp / (tp + fp):.2%}   Recall {tp / (tp + fn):.2%}   Correct lag {lag_ok / lag_n:.2%}")
