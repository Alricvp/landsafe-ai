import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from src.api.main import app  # noqa: E402


def test_endpoints():
    with TestClient(app) as c:
        assert c.get("/health").json() == {"status": "ok"}
        patients = c.get("/patients").json()
        pid = patients[0]["patient_id"]
        r = c.get(f"/patients/{pid}/risk?days=30").json()
        assert r["today"]["band"] in {"Low", "Moderate", "High"} and len(r["series"]) == 30
        assert "triggers" in c.get(f"/patients/{pid}/triggers").json()
        assert c.get("/patients/NOPE/risk").status_code == 404


def test_predict_validation():
    with TestClient(app) as c:
        log = {"day": "2026-01-01", "stress": 4, "sleep_hours": 7, "meds_taken": 1, "symptom_score": 3}
        assert c.post("/predict", json={"logs": [log] * 3}).status_code == 422
        logs = [dict(log, day=f"2026-01-{d:02d}") for d in range(1, 15)]
        assert c.post("/predict", json={"logs": logs}).status_code == 200
