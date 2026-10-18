# AquaSentinel — Solution Document

**Problem statement:** Development of Indigenous Leak Detection Sensor Systems for Operation & Maintenance of Water Supply Pipelines

**What this document is:** the complete engineering solution — what we build, how the physics works, what each component costs, how we prove it works, and the order in which we build it. No slides required.

> For how this differs from everything else that already exists, see [INNOVATION.md](INNOVATION.md).
>
> For the municipal water-loss / NRW / theft framing of this same hardware build — the water balance, the incremental bill, and the revised 4-minute script — see [NRW.md](NRW.md).

---

## 1. What "solving it" actually means

A leak detection system is only useful if it answers four questions, fast enough to act on:

| Question | Target answer | Why it matters |
|---|---|---|
| Is there a leak? | Yes / no, within minutes of it starting | Crews can't chase ghosts every day |
| Where is it? | Within ~10–20 m along the pipe | Saves digging up the wrong road |
| How bad is it? | Litres per minute lost | Prioritises big leaks over small ones |
| What do we do? | Ticket with location, severity, parts | Turns detection into a repair |

Every design choice below serves those four answers. Anything that doesn't serve them is out of scope.

---

## 2. The system in one picture

```
  ┌──────────────┐   leak noise      ┌──────────────┐   leak noise   ┌──────────────┐
  │  NODE A      │ ───────────────▶  │  NODE B      │ ─────────────▶  │  NODE C      │
  │ mic + ESP32  │                   │ mic + ESP32  │                  │ mic + ESP32  │
  │ FFT + ML     │◀── LoRa / Wi-Fi ──┤ FFT + ML     │◀─────────────────┤ FFT + ML     │
  └──────┬───────┘                   └──────┬───────┘                  └──────┬───────┘
         │   "leak detected @ 87% conf"     │                                │
         └──────────────┬───────────────────┴────────────────────────────────┘
                        ▼
              ┌───────────────────┐
              │ LOCAL GATEWAY     │  LoRaWAN concentrator / Wi-Fi at pump house
              └─────────┬─────────┘
                        ▼
              ┌───────────────────┐        ┌──────────────────────────┐
              │ FastAPI backend   │──────▶ │ PWA dashboard + SMS      │
              │ REST + WebSocket  │        │ map, spectrum, work order│
              └───────────────────┘        └──────────────────────────┘

  Zone layer (separate, cheap, catches what acoustics miss):
  [flow meter + pressure sensor at zone inlet] ──▶ night-flow loss in L/min ──▶ alert
```

Three layers, each useful alone, better together:

- **Layer 1 — Edge nodes (₹2,000–2,500 each):** listen, decide on-node, raise an event.
- **Layer 2 — Localization:** two or more nodes turn that event into a position on the map.
- **Layer 3 — Monitoring:** dashboard, map, alerts, work orders.
- **Zone layer (₹1,000–1,500, optional but recommended):** flow + pressure at the zone inlet quantify the loss continuously, 24/7, even when nobody is listening for noise.

---

## 3. The physics we exploit

A leak is not silent. Pressurised water escaping through a crack or a failed joint creates a turbulent jet whose noise couples into the pipe wall and travels along it. Three consequences we build on:

1. **Leak noise is broadband and distinctive.** Energy concentrated roughly in 200 Hz – 8 kHz, with a hissing character that differs from the low-frequency hum of pumps and the sharp clicks of valve operations. This is why every commercial correlator on the market works this way — and why we can do it cheaply.
2. **The noise arrives at two sensors at different times.** Structure-borne sound travels in a water-filled pipe at roughly **1,000–1,200 m/s** (faster than air by ~5×). A leak 50 m past sensor B is heard by B noticeably earlier than by sensor A. That time difference *is* the location.
3. **A zone that leaks keeps flowing when it shouldn't.** Between 02:00 and 04:00, a healthy network's flow drops to a small baseline. Excess flow at night is leakage — this is the industry-standard "minimum night flow" test, and it tells us the *size* of the loss, not just the location.

We deliberately do **not** claim to reinvent these principles — we industrialise them at a price a small water works can afford, with a node that thinks for itself.

---

## 4. Layer 1 — The edge node

### 4.1 Sensing front end

| Option | Cost | Notes |
|---|---|---|
| **MEMS microphone (e.g. INMP441, I²S)** | ₹120–180 | Easiest to build, no bias circuit, sensitive to air + structure noise. Our choice for the prototype. |
| Piezo accelerometer / piezo film | ₹150–400 | More structure-borne, rejects air noise better, needs conditioning + AGC. Upgrade path. |
| Ordinary electret mic | ₹30 | Picks up fans, vehicles, people — too noisy for pipe work. Avoid. |

**Mounting matters more than the sensor.** The microphone must be rigidly coupled to the pipe wall — a strap with epoxy or a magnetic clamp base, never a loose sticker. Mount at an accessible point (valve chamber, existing tapping) 100–300 m apart. We log the mounting method with each installation, because a bad mount is the single biggest cause of false negatives.

### 4.2 On-node signal processing

1. Wake on a duty cycle or a sound-trigger threshold (cheap gate on energy in the leak band).
2. Capture **8–22 kHz** audio in short bursts (e.g. 2–8 s) into a ring buffer.
3. Band-pass filter 200 Hz – 8 kHz, take the envelope.
4. **FFT (512-point)** → compute features:
   - RMS energy in 8 log-spaced bands
   - total RMS and peak-to-RMS ratio
   - spectral centroid and rolloff
   - kurtosis (leak noise is impulsive/hissy, pumps are tonal)
5. Classify with a small model (§4.3).
6. If "leak": upload the raw burst (or its spectrum) so the backend can correlate, then raise an event.

All of this runs on an ESP32 in milliseconds; we never stream raw audio continuously — that would kill the battery.

### 4.3 The classifier (on-device ML, not buzzwords)

- **Model:** logistic regression or a shallow gradient-boosted tree on the ~12 features above. Small enough to run on a microcontroller, interpretable enough to debug, and it doesn't pretend to need millions of samples.
- **Training data:** recorded on the lab rig (leak open/closed, hole sizes, background noise, pump on/off, valve operations) plus EPANET-simulated events for augmentation.
- **Deployment:** coefficients are exported to a C array and compiled into firmware — the node classifies locally, so detection still works with no connectivity.
- **False alarms:** rolling per-site baseline (median + MAD of recent features). An event must exceed baseline by a margin before it fires, and the threshold has hysteresis so a marginal leak doesn't chatter alerts.
- **Why not a deep network:** a bigger model would not measurably beat this on the data we can realistically collect, and it would cost battery, RAM, and credibility. Honest engineering beats a bigger model here.

### 4.4 Hardware and cost (per node, prototype quantity)

| Item | Spec | ₹ (approx) |
|---|---|---|
| MCU | ESP32 (already used in our existing node) | 400 |
| MEMS microphone | INMP441, I²S | 150 |
| Signal conditioning + PCB | op-amp, filter, connectors | 250 |
| Radio | LoRa SX1278 (or Wi-Fi if mains-powered sites) | 350 |
| MCU + radio PCB | 2-layer | 300 |
| Solar + charge + battery | 6 V 3 W panel, TP4056, 2× 18650 | 550 |
| Enclosure | IP65 ABS, cable glands | 350 |
| Mounting | clamp base + epoxy + strap | 150 |
| **Total** | | **~₹2,500** |

Commercially, acoustic correlators cost lakhs per set plus trained operators. A ₹2,500 node that a water works can install itself is the entire pitch.

### 4.5 Power budget (why solar works)

- Continuous listening at 22 kHz would draw ~120 mA — that's the naive design and it's why nobody does it on solar.
- Our duty cycle: listen 6 s every 10 min, plus a few seconds on any trigger → average ~6 mA.
- Daily draw ≈ 6 mA × 24 h × 3.7 V ≈ 0.53 Wh. A 6 V 3 W panel with a 2× 18650 pack (≈ 6 Wh) covers it with large margin, even through monsoon weeks.
- Store-and-forward: the node buffers events to flash and uploads when the link returns.

---

## 5. Layer 2 — Localization: turning sound into a position

### 5.1 The math

With two nodes **A** and **B** separated by known spacing **D**, both record the same leak event:

1. Align the two recordings on a common time base (gateway timestamp at event trigger).
2. Cross-correlate; find the lag **τ** (in seconds) at which the correlation peaks.
3. With wave speed **a** ≈ 1,050 m/s:

```
distance from A to leak  =  (D − a·τ) / 2      (leak between the nodes)
```

With three or more nodes, least-squares over all pairs removes ambiguity and improves accuracy.

**Confidence = the height of the correlation peak** (normalised). A low, broad peak means "something happened near here" — we then alert at zone level rather than pinning a false pin on the map. Reporting uncertainty honestly is a feature, not a weakness.

### 5.2 What limits accuracy (state this before a judge does)

- **Wave speed varies** with pipe material, diameter, and water temperature (±5–10%). We calibrate per site using the known node spacing, which removes most of this error.
- **Reflections and couplings** (valves, bends, branches) can create multiple correlation peaks; we use the physically consistent peak, not the largest.
- **Background noise** (traffic, pumps) raises the noise floor; low-traffic pipe runs and a quiet-hour analysis window are part of the deployment recipe.

### 5.3 Honest accuracy expectations

| Setup | Expected localization error |
|---|---|
| 2 nodes, 200 m apart, quiet site, leak ≥ 6 mm | ±10–20 m |
| 3 nodes, 100–150 m apart, same conditions | ±5–10 m |
| Small leak (2–4 mm) with high background noise | zone-level only |

These are targets to be measured on the rig — the validation plan (§8) exists precisely so we report measured numbers, not claims.

### 5.4 A second method for large mains

For big trunk mains, acoustic correlation gets hard. There we use **pressure transients** instead: a sudden event (pump trip, valve slam, or a burst) sends a water-hammer pressure wave down the pipe at ~1,000 m/s; two fast-sampling pressure loggers (≥200 Hz) time its arrival and locate the event the same way. Same backend, same map, different sensor head.

---

### 5.5 Simulation check (runnable today, zero cost)

Before spending a rupee on hardware we tested the maths itself. `sim_localize.py` (plain Python, no libraries) simulates what two microphones would hear and recovers the leak position:

```
$ python sim_localize.py
 true (m)   gap expect   gap found   estimate    error    conf
    111.1          148         148      111.2     +0.0   0.679
    133.3           63          64      133.2     -0.1   0.636
    166.7          -63         -64      166.8     +0.1   0.634
    188.9         -148        -148      188.8     -0.0   0.647
AVERAGE ERROR 0.1 m | VERDICT: PASS
CONTROL (no leak): confidence 0.128 -> PASS - stays quiet
```

**How strong does the leak have to be?** Sweeping the leak-to-background ratio (SNR):

| Leak vs background | Result |
|---|---|
| 6:1, 4:1, 3:1, 2:1 | 0.1 m average error |
| 1:1 (leak as loud as the noise) | 22 m average error — **fails** |

**What this tells us about the hardware:** the leak must arrive at the sensors roughly **twice as loud as the background**. That single number decides three things — the microphone choice, the mounting quality, and the node spacing. It also tells us the honest failure mode: when the leak is too quiet, the system must fall back to a zone-level alert (confidence drops) rather than showing a confident wrong pin.

**Caveats (state these, don't hide them):** this simulation has no reflections from valves or bends, no pipe-wall dispersion, no real background noise, and it assumes the leak sits *between* two sensors. A leak beyond both sensors gave a pinned estimate with mid-range confidence (0.45) — so confidence alone does not perfectly separate "localisable" from "outside the pair". Real deployments use three or more nodes, and treat a mid-confidence fix as "go and look", not "dig here".

---

## 6. The zone layer (catches what acoustics miss)

At each zone (DMA) inlet we install:

- **Flow meter** (magnetic, clamp-on or inline): total litres into the zone.
- **Pressure logger**: inlet pressure, 1-minute sampling.

Software computes:

- **Minimum night flow** over a rolling 7 days vs the expected night baseline → **leakage in L/min**.
- **Pressure stability**: steady pressure + excess flow = almost certainly a leak (as opposed to a demand event).
- **Trend alerts**: leakage rate rising above a threshold → ticket, even if nobody heard an acoustic event.

This layer is cheap, boring, and catches the small chronic leaks that produce the largest total loss — the ones acoustic nodes will miss.

---

## 7. Layer 3 — Software (mostly reused, which is our advantage)

We already run a FastAPI + WebSocket + installable PWA + SMS stack from our previous deployed project. Reused as-is: authentication, live data streaming, dashboard shell, alerting. New work is leak-specific:

- **Ingest endpoints** for node events (burst ID, spectrum, confidence, battery, RSSI).
- **Event correlation service:** pairs events from neighbouring nodes, runs cross-correlation, emits a located leak with confidence.
- **Dashboard views:**
  - Live waveform + spectrum per node (during an event)
  - Pipeline map with leak pins, confidence, severity, status (open / dispatched / repaired)
  - Node health: battery, last seen, RSSI, mounting photo
  - Zone panel: night-flow loss in L/min, pressure trend
- **Alerting:** SMS / WhatsApp to the duty engineer — *"Zone 3, chainage 340 m: probable leak, 87% confidence, est. 4.2 L/min. Ticket AS-118."*
- **Offline tolerance:** nodes store-and-forward; the dashboard shows "last seen" honestly instead of pretending data is live.
- **Maintenance planning:** leak history → repeat-failure hotspots → predicted replacement sections (pipes that fail repeatedly get flagged before they burst).

---

## 8. Validation — how we prove it (the part that wins hackathons)

Untested claims lose. This is the experiment plan.

### 8.1 Laboratory rig (₹3,000–5,000)

- ~30 m of PVC pipe on supports, pump (0.5–1 HP), butterfly valves, pressure gauge.
- **Leak plates at known chainages** (5 m, 12 m, 20 m, 28 m) with interchangeable orifices: 2, 4, 6, 8 mm.
- Background noise source (pump hum, valve clicks, a recorded traffic clip played through a speaker).
- Reference flow meter for ground truth.

### 8.2 Test matrix and metrics

| Variable | Values |
|---|---|
| Leak orifice | 2, 4, 6, 8 mm |
| Line pressure | 1, 2, 3, 5 bar |
| Background noise | quiet, pump running, pump + traffic clip |
| Node spacing | 10 m, 20 m |

**Metrics we will report (measured, not claimed):**

- Detection rate (% of leak events caught) by orifice size and noise level
- False alarms per hour in each noise condition
- **Localization error in metres** vs the known chainage
- Detection latency (seconds from leak start to alert)

### 8.3 Simulation for training data

- **EPANET** (free, EPA) to model pressure/flow behaviour with leaks added — gives physically correct feature distributions we cannot get otherwise.
- A 1-D water-hammer model to synthesise transient waveforms for the pressure-based method.
- Rig recordings label the real acoustic signatures.

### 8.4 Field pilot

- 3–5 nodes on a real network (campus or a nearby panchayat/municipal line) for 2–4 weeks.
- Ground truth via **meter-drop (step) test**: isolate sub-zones, measure flow change — the industry standard for confirming a leak location.
- We publish the before/after water-loss number for the pilot zone.

---

## 9. Risks and honest limitations

| Risk | Mitigation |
|---|---|
| Background noise causes false alarms | Quiet-hour windows, per-site self-calibration, zone-layer confirmation before dispatch |
| Small leaks acoustically weak | Zone layer (night flow) catches what acoustics misses; that's why both layers exist |
| Bad mounting kills sensitivity | Installation protocol with photos; mounting logged per node |
| Clock drift breaks time-difference maths | Sync on event via gateway; per-site calibration of wave speed |
| Pipe material changes wave speed | Calibrate per site using known node spacing |
| Vandalism / theft in the field | Low-profile enclosure, flush mounting, no visible branding |

We would rather state these than be caught by them.

---

## 10. Build order (this is the execution plan)

1. **Rig** — build the PVC test bench with controlled leak points.
2. **Node v1** — mic capture → FFT → band energies → CSV over Wi-Fi. No ML yet; just prove the signal is visible.
3. **Correlation** — two microphones on the rig, cross-correlation in Python, print estimated vs actual distance. This is the make-or-break experiment.
4. **Classifier** — record rig dataset (label every condition), train, export to C, run on-node, verify identical decisions.
5. **Localization service** — the validated correlation moved into the backend, producing map pins with confidence.
6. **Zone layer** — flow + pressure logging, night-flow analysis.
7. **Dashboard + alerts** — leak views on the existing PWA, SMS workflow.
8. **Field pilot** — install, run, measure, publish the numbers.

Milestones: rig + signal visible (week 1–2) · localization proven (week 3–4) · on-node classifier (week 5–6) · dashboard + zone layer (week 7–8) · pilot + write-up (week 9–10).

---

## 11. What we bring that others don't

- **A deployed platform already exists.** The backend, live dashboard, SMS alerting, and solar ESP32 node are not promises — they are running code from our previous project. Only the sensing head and the leak algorithm are new.
- **Indian-scale economics.** ₹2,500 nodes designed to be installed by a two-person water works crew, not a vendor.
- **Honest, measured claims.** Every number in this document is a target with a test attached to it.

---

## 12. First-week shopping list (to start immediately)

- 2 × INMP441 MEMS mic + breakout (₹300)
- 2 × ESP32 dev boards (₹800)
- 10 m PVC pipe + fittings + butterfly valve (₹800)
- Small pump + hose (₹1,200)
- Drill bits for 2/4/6/8 mm leak orifices (₹200)
- Reference flow meter (₹800–1,200)
- 6 V 3 W solar panel + 18650 cells + TP4056 (₹550)
- Multimeter, jumper wires, breadboards (₹500)

Total ≈ ₹5,000–6,000, and it buys a rig that can validate the entire idea.

---

## 13. Questions judges will ask — with our answers

**"Why not just put flow meters everywhere?"** Flow meters tell you a zone is losing water; they don't tell you where, and each one costs more than our node. We use one flow meter per zone (the zone layer) and many cheap acoustic nodes inside it (the localization layer).

**"How accurate is it, really?"** Measured on a rig with known leak positions, reported as ±X m for a given orifice size and noise level. Where accuracy degrades (very small leaks, very noisy sites), we degrade to a zone-level alert rather than a false precise pin.

**"What if there's no internet?"** Detection is on-node; nodes buffer events to flash and upload when the link returns. The dashboard shows last-seen honestly.

**"How is this different from commercial correlators?"** Roughly 50–100× cheaper per listening point, no trained operator required, continuous monitoring instead of periodic sweeps, and it reports location with a confidence score instead of a technician's ear.

**"Can a small water works actually run this?"** The node needs only a clamp and a solar panel; the dashboard runs on any phone browser; the zone layer is one flow meter. Total district-scale cost is a fraction of one commercial correlator.