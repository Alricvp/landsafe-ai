"""FlareGuard dashboard.   streamlit run app/dashboard.py

Talks to the API only (set API_URL), so it can run on a different machine
from the server that hosts the model.
"""
import os

import altair as alt
import pandas as pd
import requests
import streamlit as st

API = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
BAND_COLOR = {"Low": "#0F766E", "Moderate": "#B7791F", "High": "#B42318"}

st.set_page_config(page_title="FlareGuard", page_icon="🩺", layout="wide")
st.markdown(
    """
    <style>
      .risk-number {font-size: 4.2rem; font-weight: 700; line-height: 1;}
      .band {font-size: 1.1rem; font-weight: 600; margin-top: .3rem;}
      .note {color: #4B6670; font-size: .9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=60, show_spinner=False)
def api_get(path, **params):
    r = requests.get(f"{API}{path}", params=params, timeout=60)
    r.raise_for_status()
    return r.json()


try:
    patients = api_get("/patients")
    model = api_get("/model")
except requests.RequestException:
    st.error(f"Can't reach the FlareGuard API at {API}. Start it with `make api`, "
             "or set API_URL to the server's address.")
    st.stop()

# ---- sidebar -----------------------------------------------------------------
with st.sidebar:
    st.header("FlareGuard")
    st.caption("Synthetic patients only. Not medical advice.")
    held_out_only = st.toggle("Only patients the model never saw", value=True)
    pool = [p for p in patients if p["held_out"]] if held_out_only else patients
    pid = st.selectbox("Patient", [p["patient_id"] for p in pool])
    window = st.slider("Days shown", 14, 180, 60)
    m = model["metrics"]
    st.divider()
    st.caption(
        f"Model check on {m['n_test_patients']} unseen patients: "
        f"AUC {m['auc']:.2f} (looking at today's symptoms alone: {m['baseline_auc_todays_symptoms']:.2f})."
    )

report = api_get(f"/patients/{pid}/risk", days=window)
today = report["today"]
horizon = report["horizon_days"]

st.title("Flare risk")
st.write(f"Chance of a flare in the next {horizon} days, and what is pushing it up or down.")

# ---- headline ----------------------------------------------------------------
left, right = st.columns([1, 3])
with left:
    color = BAND_COLOR[today["band"]]
    st.markdown(f"<div class='risk-number' style='color:{color}'>{today['risk']:.0%}</div>"
                f"<div class='band' style='color:{color}'>{today['band']} risk</div>"
                f"<div class='note'>as of {today['day']}</div>", unsafe_allow_html=True)

series = pd.DataFrame(report["series"])
series["day"] = pd.to_datetime(series["day"])
with right:
    line = alt.Chart(series).mark_line(color="#12303A", strokeWidth=2).encode(
        x=alt.X("day:T", title=None),
        y=alt.Y("risk:Q", title=f"{horizon}-day flare risk", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")),
        tooltip=[alt.Tooltip("day:T"), alt.Tooltip("risk:Q", format=".0%")],
    )
    layers = [line]
    if "flare" in series.columns:
        flares = series[series["flare"] == True]  # noqa: E712
        if not flares.empty:
            layers.append(alt.Chart(flares).mark_point(color=BAND_COLOR["High"], size=60, filled=True, y=0).encode(
                x="day:T", tooltip=[alt.Tooltip("day:T", title="Flare day")]))
    st.altair_chart(alt.layer(*layers).properties(height=240), use_container_width=True)
    if "flare" in series.columns:
        st.caption("Red dots mark days the patient was actually in a flare.")

# ---- explanations ------------------------------------------------------------
def effect_chart(rows, value_key, title):
    df = pd.DataFrame(rows)
    df["points"] = df[value_key] * 100
    df["direction"] = df["points"].apply(lambda v: "Raises risk" if v > 0 else "Lowers risk")
    return alt.Chart(df).mark_bar().encode(
        y=alt.Y("label:N", sort=None, title=None),
        x=alt.X("points:Q", title=title),
        color=alt.Color("direction:N", legend=None,
                        scale=alt.Scale(domain=["Raises risk", "Lowers risk"], range=[BAND_COLOR["High"], BAND_COLOR["Low"]])),
        tooltip=["label", alt.Tooltip("points:Q", format="+.1f", title="Points")],
    ).properties(height=210)


c1, c2 = st.columns(2)
with c1:
    st.subheader("What is driving risk today")
    st.altair_chart(effect_chart(today["drivers"], "contribution", "Percentage points vs. an average day"),
                    use_container_width=True)
with c2:
    st.subheader("What changed since yesterday")
    st.altair_chart(effect_chart(today["changes"], "delta", "Change in percentage points"),
                    use_container_width=True)

# ---- triggers ----------------------------------------------------------------
st.subheader("This patient's likely triggers")
try:
    trig = api_get(f"/patients/{pid}/triggers")["triggers"]
except requests.RequestException:
    trig = []
found = [t for t in trig if t["is_trigger"]]
if found:
    for t in found:
        st.markdown(f"- {t['summary']}")
else:
    st.write("No clear triggers found in this patient's logs yet.")

with st.expander("Details for every factor tested"):
    table = pd.DataFrame([{
        "Factor": t["label"],
        "Best lag (days)": t["best_lag_days"],
        "Effect (symptom points)": round(t["effect"], 2),
        "95% range": f"{t['ci_low']:.2f} to {t['ci_high']:.2f}",
        "Adjusted p": f"{t['q_value']:.3g}",
        "Trigger?": "Yes" if t["is_trigger"] else "No",
    } for t in trig])
    st.dataframe(table, hide_index=True, use_container_width=True)

with st.expander("Demo check: triggers planted in the synthetic data"):
    truth = api_get(f"/patients/{pid}/ground-truth")["planted_triggers"]
    planted = {k for k in truth}
    detected = {t["factor"] for t in found}
    st.write(f"Planted: {', '.join(sorted(planted)) or 'none'}")
    st.write(f"Found: {', '.join(sorted(detected)) or 'none'}")
    st.write(f"Matched {len(planted & detected)} of {len(planted)} planted triggers; "
             f"{len(detected - planted)} extra.")
