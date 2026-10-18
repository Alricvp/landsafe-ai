"""Central settings. Everything can be overridden with environment variables."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("FLAREGUARD_DATA_DIR", ROOT / "data" / "synthetic"))
MODEL_DIR = Path(os.getenv("FLAREGUARD_MODEL_DIR", ROOT / "models"))

LOGS_PATH = DATA_DIR / "daily_logs.csv"
TRUTH_PATH = DATA_DIR / "ground_truth.json"
MODEL_PATH = MODEL_DIR / "flare_model.joblib"

N_PATIENTS = int(os.getenv("FLAREGUARD_N_PATIENTS", "60"))
N_DAYS = int(os.getenv("FLAREGUARD_N_DAYS", "365"))
SEED = int(os.getenv("FLAREGUARD_SEED", "42"))
HORIZON_DAYS = int(os.getenv("FLAREGUARD_HORIZON_DAYS", "7"))

# Daily-log fields a patient (or the app) must supply.
LOG_FIELDS = [
    "day", "dairy_servings", "alcohol_units", "stress",
    "sleep_hours", "meds_taken", "nsaid", "symptom_score",
]

# Exposures the causal module tests, all oriented so that "more" = potentially worse.
EXPOSURES = [
    "dairy_servings", "alcohol_units", "stress",
    "sleep_deficit", "meds_missed", "nsaid",
]

LABELS = {
    "dairy_servings": "Dairy",
    "alcohol_units": "Alcohol",
    "stress": "Stress",
    "sleep_deficit": "Short sleep",
    "meds_missed": "Missed medication",
    "nsaid": "NSAID painkillers",
    "symptom_score": "Recent symptoms",
}

UNITS = {
    "dairy_servings": "per serving",
    "alcohol_units": "per drink",
    "stress": "per stress point",
    "sleep_deficit": "per hour under 7",
    "meds_missed": "per missed day",
    "nsaid": "per day taken",
}

# Risk bands for the 7-day flare probability.
BAND_MODERATE = float(os.getenv("FLAREGUARD_BAND_MODERATE", "0.25"))
BAND_HIGH = float(os.getenv("FLAREGUARD_BAND_HIGH", "0.55"))


def band(risk: float) -> str:
    if risk >= BAND_HIGH:
        return "High"
    if risk >= BAND_MODERATE:
        return "Moderate"
    return "Low"
