"""Framework-free logic behind the API (easy to unit test)."""
import json

import pandas as pd

from src import config
from src.bootstrap import ensure_artifacts
from src.causal.triggers import detect_triggers
from src.explain.local import explain_last_two_days
from src.features.build import build_features
from src.models.train import load_bundle

MIN_LOG_DAYS = 7


class FlareService:
    def __init__(self):
        ensure_artifacts()
        self.bundle = load_bundle()
        self.logs = pd.read_csv(config.LOGS_PATH, parse_dates=["day"])
        self.truth = json.loads(config.TRUTH_PATH.read_text())
        self.patient_ids = sorted(self.logs["patient_id"].unique())
        self.held_out = set(self.bundle["test_patients"])
        self.features = build_features(self.logs, horizon=self.bundle["horizon"], with_target=False)

    # ---- helpers -------------------------------------------------------------
    def _require(self, pid):
        if pid not in self.held_out and pid not in self.patient_ids:
            raise KeyError(pid)

    def _risk_for(self, feats):
        return self.bundle["model"].predict_proba(feats[self.bundle["feature_names"]])[:, 1]

    def _report(self, feats, logs, days):
        feats = feats.sort_values("day").reset_index(drop=True)
        if len(feats) < 2:
            raise ValueError(f"Need at least {MIN_LOG_DAYS + 1} days of logs to forecast.")
        feats = feats.assign(risk=self._risk_for(feats))
        today_risk, drivers, changes = explain_last_two_days(self.bundle, feats)
        merged = feats[["day", "risk"]].merge(
            logs[[c for c in ["day", "symptom_score", "flare"] if c in logs.columns]], on="day", how="left")
        series = []
        for _, r in merged.tail(days).iterrows():
            point = {"day": r["day"].strftime("%Y-%m-%d"), "risk": round(float(r["risk"]), 4),
                     "symptom_score": float(r["symptom_score"])}
            if "flare" in merged.columns and pd.notna(r.get("flare")):
                point["flare"] = bool(r["flare"])
            series.append(point)
        return {
            "horizon_days": self.bundle["horizon"],
            "series": series,
            "today": {
                "day": series[-1]["day"],
                "risk": round(today_risk, 4),
                "band": config.band(today_risk),
                "drivers": drivers,
                "changes": changes,
            },
        }

    # ---- public API ----------------------------------------------------------
    def model_info(self):
        return {"horizon_days": self.bundle["horizon"], "metrics": self.bundle["metrics"],
                "n_patients": len(self.patient_ids)}

    def patients(self):
        last = self.features.groupby("patient_id").tail(1).set_index("patient_id")
        risks = pd.Series(self._risk_for(last), index=last.index)
        out = []
        for pid in self.patient_ids:
            out.append({"patient_id": pid, "held_out": pid in self.held_out,
                        "latest_risk": round(float(risks.get(pid, float("nan"))), 4),
                        "latest_band": config.band(float(risks.get(pid, 0)))})
        return out

    def risk(self, pid, days=60):
        self._require(pid)
        feats = self.features[self.features.patient_id == pid]
        logs = self.logs[self.logs.patient_id == pid]
        report = self._report(feats, logs, days)
        report.update({"patient_id": pid, "held_out": pid in self.held_out})
        return report

    def triggers(self, pid):
        self._require(pid)
        return {"patient_id": pid, "triggers": detect_triggers(self.logs[self.logs.patient_id == pid])}

    def ground_truth(self, pid):
        self._require(pid)
        return {"patient_id": pid, "planted_triggers": self.truth.get(pid, {})}

    def predict(self, rows, days=60):
        """rows: list of dicts with config.LOG_FIELDS. Returns the same report as risk()."""
        if len(rows) < MIN_LOG_DAYS + 1:
            raise ValueError(f"Need at least {MIN_LOG_DAYS + 1} days of logs (got {len(rows)}).")
        logs = pd.DataFrame(rows)
        logs["day"] = pd.to_datetime(logs["day"])
        feats = build_features(logs, horizon=self.bundle["horizon"], with_target=False)
        return self._report(feats, logs, days)

    def predict_triggers(self, rows):
        return {"triggers": detect_triggers(pd.DataFrame(rows))}
