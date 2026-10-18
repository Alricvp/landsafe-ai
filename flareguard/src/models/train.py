"""Train the 7-day flare forecaster.

Patients (not rows) are split into train / held-out so the reported score reflects
how the model behaves on people it has never seen.

    python -m src.models.train
"""
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from src import config
from src.features.build import build_features, feature_names


def _split_patients(ids, seed, test_frac=0.25):
    ids = sorted(ids)
    rng = np.random.default_rng(seed)
    rng.shuffle(ids)
    n_test = max(1, int(round(len(ids) * test_frac)))
    return sorted(ids[n_test:]), sorted(ids[:n_test])


def train_model(df=None, horizon=None, seed=None):
    seed = config.SEED if seed is None else seed
    horizon = horizon or config.HORIZON_DAYS
    if df is None:
        df = pd.read_csv(config.LOGS_PATH)

    feats = build_features(df, horizon=horizon, with_target=True)
    names = feature_names()
    train_ids, test_ids = _split_patients(feats["patient_id"].unique().tolist(), seed)
    tr = feats[feats.patient_id.isin(train_ids)]
    te = feats[feats.patient_id.isin(test_ids)]

    model = HistGradientBoostingClassifier(
        max_depth=4, learning_rate=0.06, max_iter=250,
        l2_regularization=1.0, random_state=seed,
    )
    model.fit(tr[names], tr["target"])
    proba = model.predict_proba(te[names])[:, 1]

    metrics = {
        "auc": float(roc_auc_score(te["target"], proba)),
        "average_precision": float(average_precision_score(te["target"], proba)),
        "brier": float(brier_score_loss(te["target"], proba)),
        "baseline_auc_todays_symptoms": float(roc_auc_score(te["target"], te["symptom_score_lag0"])),
        "base_rate": float(te["target"].mean()),
        "n_train_patients": len(train_ids),
        "n_test_patients": len(test_ids),
        "n_test_rows": int(len(te)),
    }
    return {
        "model": model,
        "feature_names": names,
        "means": tr[names].mean().to_dict(),
        "horizon": horizon,
        "train_patients": train_ids,
        "test_patients": test_ids,
        "metrics": metrics,
    }


def train_and_save():
    bundle = train_model()
    config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, config.MODEL_PATH)
    return bundle


def load_bundle():
    return joblib.load(config.MODEL_PATH)


if __name__ == "__main__":
    b = train_and_save()
    print("Saved", config.MODEL_PATH)
    for k, v in b["metrics"].items():
        print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")
