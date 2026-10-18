"""FlareGuard API.   uvicorn src.api.main:app --host 0.0.0.0 --port 8000

Interactive docs are served at /docs.
"""
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src import config
from src.api.service import FlareService

_state = {}


@asynccontextmanager
async def lifespan(app):
    _state["svc"] = FlareService()
    yield
    _state.clear()


app = FastAPI(
    title="FlareGuard API",
    version="0.1.0",
    description="Seven-day IBD flare forecasts with explanations and personal trigger detection.",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def svc():
    return _state["svc"]


class DailyLog(BaseModel):
    day: str = Field(..., description="ISO date, e.g. 2026-03-14")
    dairy_servings: float = Field(0, ge=0, le=20)
    alcohol_units: float = Field(0, ge=0, le=30)
    stress: float = Field(..., ge=0, le=10)
    sleep_hours: float = Field(..., ge=0, le=24)
    meds_taken: int = Field(..., ge=0, le=1, description="1 if all prescribed medication was taken")
    nsaid: int = Field(0, ge=0, le=1)
    symptom_score: float = Field(..., ge=0, le=10)


class LogBatch(BaseModel):
    logs: List[DailyLog]
    days: Optional[int] = 60


def _rows(batch):
    return [{f: getattr(log, f) for f in config.LOG_FIELDS} for log in batch.logs]


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown patient id.")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/model")
def model_info():
    return svc().model_info()


@app.get("/patients")
def patients():
    return svc().patients()


@app.get("/patients/{patient_id}/risk")
def patient_risk(patient_id: str, days: int = Query(60, ge=7, le=365)):
    return _call(svc().risk, patient_id, days)


@app.get("/patients/{patient_id}/triggers")
def patient_triggers(patient_id: str):
    return _call(svc().triggers, patient_id)


@app.get("/patients/{patient_id}/ground-truth")
def patient_ground_truth(patient_id: str):
    """Demo only: the triggers planted in the synthetic data for this patient."""
    return _call(svc().ground_truth, patient_id)


@app.post("/predict")
def predict(batch: LogBatch):
    """Send at least 8 days of logs; get today's risk, drivers and what changed."""
    return _call(svc().predict, _rows(batch), batch.days or 60)


@app.post("/triggers")
def triggers(batch: LogBatch):
    """Send at least 60 days of logs; get that person's likely triggers."""
    return _call(svc().predict_triggers, _rows(batch))
