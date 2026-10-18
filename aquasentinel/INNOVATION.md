# AquaSentinel — The Innovation Layer

**This document answers one question: what do we do that isn't already done?**

Short answer: we stop treating "leak detection" as a water-loss problem and treat it as a **water-safety** problem. Our system tells the utility not just *where the water is escaping*, but **which leak was open when the pipe went negative-pressure — i.e. which leak actually let contaminated soil into the drinking water, and whose taps must be flushed first.**

---

## 1. Honest novelty audit (what already exists)

Before claiming novelty, here is what is already available in the world — so we never embarrass ourselves in front of a judge:

| Technique | Status |
|---|---|
| Acoustic leak detection & correlation | Commercial since the 1980s (Sewerin, Goldfish, Mueller). Mature, expensive. |
| Time-difference-of-arrival localization | Standard inside every commercial correlator |
| **"Acoustic + AI" leak detection** | **Crowded** — at least half a dozen papers (2024–2026) and Edge Impulse projects do ML on pipe audio |
| Minimum night flow analysis | Textbook industry standard |
| Water-hammer pressure timing | Classical hydraulics, decades old |
| Microbial intrusion during low/negative pressure events | Well-studied science (Besner & Propfst, *Water Research* 2011; Water Research Foundation projects) — the *physics and health risk* are established |

**Conclusion: none of the building blocks are new, and "we used AI" is no longer a differentiator.** A judge who has seen five leak-detection projects this week will have heard our current pitch already.

---

## 2. The gap we exploit

Every leak detector — including the expensive ones — answers: **"where is the water going?"**

None of them answer: **"where did germs get in?"**

That is a different and more important question in India, because a distribution network is only as safe as its **weakest moment**. When a pump trips, a valve slams shut, or a burst happens somewhere, pressure in part of the network can dip below atmospheric (**negative pressure event, NPE**). At that moment, every open leak, crack, or failed joint on that segment becomes an open door — and the water in that segment can be sucked inwards, pulling contaminated groundwater or soil into the drinking water. The leak itself is not the hazard; the leak *during an NPE* is the hazard.

**No cheap sensor system on the market measures this.** Utilities know it matters scientifically, but detecting NPEs requires high-rate pressure logging and transient monitoring that only large utilities with SCADA can afford — and even they usually cannot say which segment was exposed and for how long.

**A second, independent gap sits next to this one, and it may be easier to sell to a non-technical judge.** Meter-analytics vendors (Silverblaze, WEIOT, and about a dozen others) already sell utilities their Non-Revenue Water number in rupees per ward — and not one of them can tell you which road the water went under. Acoustic correlators can tell you the road, but they cannot do the accounting. Nobody sells both. That gap is the pitch if this project's primary audience is a municipal utility rather than a water-quality engineer: see [NRW.md](NRW.md).

---

## 3. The innovation: Ingress-Aware Leak Prioritisation (working name: **AquaSentinel Ingress**)

### 3.1 What the node measures now (small hardware delta)

The acoustic node we already planned gains **one cheap pressure sensor** (a BMP388 or MPX5015-class part, ≈₹250–350) sampled at **100 Hz**, alongside the existing acoustic burst capture. That is the entire hardware change. Everything else — the FFT, the classifier, LoRa, solar, the ₹2,500 target — stays as designed.

### 3.2 What the system produces that doesn't exist today

```
  NPE DETECTION (per zone, from 100 Hz pressure)
  ────────────────────────────────────────────
  • Flag any window where pressure < atmospheric (or < threshold) — the exposure window
  • Record: segment ID, start, duration, depth (kPa below zero)

  EXPOSURE LEDGER (the product nobody else makes)
  ────────────────────────────────────────────
  • For every active leak, was it open during an exposure window?  YES / NO
  • Risk score  =  leak open?  ×  NPE depth  ×  NPE duration  ×  population served

  RANKED RESPONSE (what the crew does first)
  ────────────────────────────────────────────
  "Segment C leak, 0.3 L/min — small, low water loss.
   BUT it was open during a -8 kPa NPE on 14 Aug, 02:41 for 47 seconds,
   serving 1,200 households.
   ACTION: repair today + flush service lines in Zone 5 before next chlorination."
```

Compare with a commercial correlator's output: *"Leak at 340 m, 4 L/min."* We output: *"Repair THIS one first, and here's who might be drinking from it."*

### 3.3 Why this is genuinely new (and honest about it)

- The **science** (NPE → intrusion) is established literature — we cite it, we don't claim it.
- The **sensor fusion at ₹2,500/node** (acoustic + 100 Hz pressure in one cheap solar node, with on-edge classification) is not something we found existing; the closest work is SCADA-grade transient monitoring that costs lakhs and needs mains power and operators.
- The **exposure ledger and risk-ranked response** is a *product concept* that doesn't exist in the leak-detection market at any price point today.
- It converts the project's purpose from **water conservation** (a utility cost problem, low political temperature) to **public health** (diarrhoeal disease prevention, high temperature, directly tied to Jal Jeevan Mission quality targets).

### 3.4 What it costs

- **+₹300 per node** (pressure sensor + connector).
- **+~2 weeks of work** (pressure logging, NPE detection algorithm, exposure ledger in the backend).
- **Zero** change to the localization algorithm or the dashboard architecture.

---

## 4. The demo that wins (rig script)

This is the 4-minute moment a judge remembers. All of it happens on the lab rig, no field site needed:

**Setup:** 30 m PVC rig, pump, two acoustic nodes at 10 m and 20 m, one pressure node, leak orifices at known positions, one closed valve for the NPE.

**The scene:** three leaks open at once:
- **Leak 1** — big (8 mm), 4 L/min, loudest, on the far segment. This is what every commercial detector screams about.
- **Leak 2** — small (3 mm), 0.3 L/min, nearly inaudible. Nobody would notice it.
- **Leak 3** — medium, open but *closed off* by a valve so it's isolated from the network.

**Act 1 (2 min):** Show the rig running. Acoustic nodes detect the noise; dashboard lights up and localises **Leak 1** to ±X m — the "expected" result, the baseline capability. Judges nod.

**Act 2 (2 min) — the turn:** Slam the valve shut. Pressure trace on the dashboard dives below zero — the system flags: *"NPE: −8 kPa, 47 s, Zone 5."*

**Act 3:** The system's ranked response screen:
- Leak 1: "high water loss, repair within week."
- **Leak 2: "small leak, but OPEN during the NPE — 1,200 households exposed. REPAIR TODAY + flush Zone 5."**
- Leak 3: "isolated by closed valve — not exposed. no action."

**The closing line:** *"Every other detector would have told us to chase the loudest leak. Ours tells us which leak actually made the water unsafe — and where to flush first."*

That demo makes the point no slide can, and it is built from ₹300 of extra hardware on a rig we already planned.

---

## 5. What to claim and what not to claim (judge-proof honesty)

**Claim confidently:**
- The physics (NPE → intrusion) — cite the literature, it's established.
- That no cheap product integrates leak localisation with ingress exposure (true today).
- Our rig-measured numbers (detection rate, localisation error, NPE depth/duration accuracy).
- That our hardware is ~50–100× cheaper than commercial equipment.

**Do NOT claim:**
- That we've invented acoustic leak detection or "AI leak detection" (we haven't; plenty exist).
- That we've solved pathogen intrusion — we detect the *conditions and windows* that permit it, not the pathogens themselves. Say it exactly this way; it is still a big deal and it is honest.
- Any accuracy number we haven't measured on the rig.

**The line that wins credibility:** *"We did not invent leak detection. We made it affordable, and we added the question the industry isn't asking: not where is the water going, but where did the germs come in."*

---

## 6. Fallback positioning

If a particular hackathon judges decide contamination science is "too researchy" for their scope, the project still stands on its own as a **₹2,500 leak detection and localisation system** (§ SOLUTION.md) — the ingress layer is an *additive* module that costs ₹300 and two weeks, never a load-bearing dependency. We can ship either version.

---

## 7. Build order with the innovation included

| Week | Deliverable |
|---|---|
| 1–2 | Rig + acoustic signal visible (baseline capability) |
| 3–4 | **Localisation proven** (cross-correlation vs known positions) — the make-or-break |
| 5–6 | On-node classifier + **pressure sensor + NPE detection** |
| 7 | **Exposure ledger + risk-ranked response** in the dashboard |
| 8 | Zone layer (night-flow loss in L/min) + SMS workflow |
| 9–10 | Field pilot + measured numbers + final demo script |

The first four weeks are the original plan; everything after is where the difference lives.