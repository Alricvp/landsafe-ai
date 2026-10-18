# FlareGuard

Seven-day IBD flare forecasts that explain themselves, plus a personal trigger detector
that tells each patient which foods and habits precede *their* bad days.

**Everything runs on synthetic data.** Real daily IBD logs are not public, so we generate
patients with *planted* triggers and check the system finds them. Not medical advice.

## What it does

| Piece | What you get | Where |
|---|---|---|
| Synthetic patients | 60 people x 365 days of diet, stress, sleep, meds, symptoms, with hidden known triggers | `src/datagen` |
| Flare forecaster | Probability of a flare in the next 7 days (gradient boosting, patient-level holdout) | `src/features`, `src/models` |
| Explanations | "What is driving risk today" and "what changed since yesterday", by factor | `src/explain` |
| Trigger detective | Lag-adjusted regression per patient; tells you the factor, the delay and the size of effect | `src/causal` |
| API | FastAPI, docs at `/docs` | `src/api` |
| Dashboard | Streamlit, talks to the API | `app/` |

## Results (seed 42, `make eval`)

- Held-out patients: AUC **0.86** vs **0.81** for "just look at today's symptoms".
- Trigger detection vs planted truth: precision **~98%**, recall **~95%**, correct lag **100%** (30 patients checked).

## Run it

```bash
cp .env.example .env
make install          # or: scripts/server_setup.sh on the Linux server
make api              # generates data + trains on first start, serves :8000
make ui               # dashboard on :8501 (set API_URL if the API is elsewhere)
make test
```

Docker: `docker compose up --build -d` (API), add `--profile ui` for the dashboard.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health`, `/model` | status, held-out metrics |
| GET | `/patients` | patients with latest risk |
| GET | `/patients/{id}/risk?days=60` | risk series, today's drivers, change since yesterday |
| GET | `/patients/{id}/triggers` | detected personal triggers |
| GET | `/patients/{id}/ground-truth` | planted triggers (demo only) |
| POST | `/predict` | send 8+ days of logs, get risk and drivers |
| POST | `/triggers` | send 60+ days of logs, get triggers |

```bash
curl localhost:8000/patients/P006/risk?days=14
```

## IBM LinuxONE (s390x) notes

- Check `uname -m`. If it prints `s390x`, PyPI has few prebuilt wheels, so use apt's
  `python3-numpy/pandas/scipy/sklearn` (what `scripts/server_setup.sh` and the `Dockerfile` do).
- The ML/causal code deliberately uses only numpy, scipy and scikit-learn (no xgboost, shap,
  statsmodels or dowhy) to keep installs painless.
- `streamlit` depends on pyarrow, which may not install on s390x. If so, run the dashboard on a
  laptop: `API_URL=http://<server-ip>:8000 streamlit run app/dashboard.py`.
- The `Dockerfile` has not been built on s390x yet; do a test build early.

## How the pieces fit

```
datagen -> daily_logs.csv --> features (lags, 7-day means) --> model --> /patients/{id}/risk
                 |                                              |
                 +--> causal (lagged regression) --> /triggers  +--> explain (occlusion by factor)
```

## Limits to state in your pitch

- Synthetic data: results show the method works when its assumptions hold, not clinical accuracy.
- Trigger detection is temporal precedence plus adjustment, not a randomized proof.
- Next steps: validate on real consented logs, add clinician-in-the-loop review, calibrate per patient.
