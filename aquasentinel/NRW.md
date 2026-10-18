# AquaSentinel NRW — Water Loss Accounting & Theft Layer

**What this document is:** how to pitch and build the *same* sensor system as a **Non-Revenue Water (NRW) and theft** product for a municipal water utility.

**Decision it implements:** municipal NRW is the lead framing. Jal Jeevan Mission / rural O&M stays as the named deployment context, not the pitch.

**Why this framing won:** the acoustics, the localization math, the ESP32 node, the pressure transient, the backend — none of it changes. What changes is the *question at the top of the pitch*. Instead of "where is the leak," the opening line becomes **"you're losing X rupees a year in this ward, and we tell you which 30 metres of street to dig."** That number survives a judge who has no interest in contamination science.

Companion documents: [SOLUTION.md](SOLUTION.md) (the engineering build) · [INNOVATION.md](INNOVATION.md) (the novelty audit and the ingress layer).

---

## 1. The buyer and the problem, in one paragraph

A municipal utility in India supplies treated water into a distribution network, bills a fraction of what it supplies, and collects even less. The gap is **Non-Revenue Water**. It has four distinct causes, and a utility that treats them as one problem will spend years replacing meters and lose the same money every month. Utilities already know they have an NRW problem — they can measure it approximately, in rupees, per ward, from bulk meters and billing data. **What they cannot do is act on it**, because the number tells you *how much* you are losing in a ward that is sometimes 40 km², and not *where*. So the standard response is bulk meter replacement, which addresses only the smallest slice of the loss.

That is the gap. Not detection. **Localization of a financial quantity.**

---

## 2. The water balance — where our money number comes from

Over a fixed billing period, for a defined ward (a DMA — District Metered Area):

```
  WATER SUPPLIED into the ward        Q_supply      (bulk meter at ward inlet)
        │
        ├─► WATER SOLD (authorised, billed)  Q_billed    (sum of consumer meters / billing records)
        │
        └─► NON-REVENUE WATER = Q_supply − Q_billed
                │
                ├── PHYSICAL LOSS  (real leaks, burst mains, weeping joints)
                ├── APPARENT LOSS  (meter under-registration, data-handling error)
                ├── AUTHORISED UNBILLED (standposts, tanker supply, public use)
                └── UNAUTHORISED USE / THEFT (illegal tap, over-coupled pump, bypassed meter)
```

This is the **IWA water balance** — the standard framework used by utilities worldwide. We are not inventing it, and we should say so: using the industry's own framework is a credibility asset, not a weakness.

**The hard truth we lead with rather than hide:** two bulk meters *cannot* separate physical loss from apparent loss. Every utility in the world knows this; it is the single most common question a water-loss specialist asks. Any pitch that claims otherwise is immediately discounted. What we do instead is described in §4 — we **resolve it by iteration**, not by inference.

---

## 3. What we add to the bill (hardware delta: almost nothing)

| Item | Qty | Cost | Why |
|---|---|---|---|
| Bulk electromagnetic flow meter, DN80–150 | 2 (ward inlet + far end) | ₹6,000–9,000 | establishes `Q_supply` and cross-checks zone isolation |
| Pressure transducer, 100 Hz + logger | 1–2 | ₹900–1,500 | already in the build for the ingress layer; reused here |
| Acoustic localisation nodes | 4–6 per pilot ward | ₹2,500 each | **already built** — this is the part nobody else has |
| Consumer-meter aggregate feed | — | ₹0 | from billing data / existing SCADA; **no new per-house instrumentation** |

Total incremental spend over the existing AquaSentinel build: **≈ ₹8,000–11,000.** The critical design property is that we instrument **two meters per ward and a handful of cheap listening nodes** — not a smart meter on every house. A ₹900 consumer meter on 10,000 connections is ₹90 lakh and still won't localise anything.

**Dependency we must be honest about:** the IWA split into physical vs apparent loss normally requires pressure testing the network (isolate a segment, watch the flow response). Our node fleet gives a cheap, continuous proxy for that — see §4 — which is itself a small novelty.

---

## 4. The core mechanism: closing the loop, not inferring

This is the argument that makes the project real. It is iterative, and each pass is independently measurable.

**Pass 1 — quantify.** Bulk meters give the ward's NRW in litres and rupees: `NRW_1 = Q_supply − Q_billed`.

**Pass 2 — localise.** Acoustic nodes locate every *physical* loss in the ward to ~10–20 m. Each leak found is a *physical loss measurement*, in litres per minute, with an address. Sum them: `L_phys`.

**Pass 3 — repair, then re-measure.** Fix the located leaks. Re-read the bulk meters after the repair settles: `NRW_2`.

**The result, and the claim we can actually make:**

```
  L_phys_measured  = NRW_1 − NRW_2      ← physical loss, now localised AND repaired
  RESIDUAL         = NRW_2              ← apparent loss + unbilled + unauthorised use
```

We never *infer* the split. We **measure it as a difference**, the same way you measure a leak by closing a valve rather than by guessing. That's rigorous, it's cheap, and it's exactly the thing the existing meter-analytics vendors cannot do — they get `NRW_1` and stop there.

**Pass 4 — characterise the residual.** Now, and only now, do we have something meaningful to say about theft, and we have a cheap, testable discriminator between it and meter error:

| Observation | Physical leak (real loss) | Unauthorised use (theft) |
|---|---|---|
| Responds to closing a zone valve | Yes — discharge falls within seconds | No — the illegal feed is on a service line that stays live |
| Discharge scales with line pressure | Yes, `Q ∝ √ΔP` | Yes, likewise (honest: this one does **not** discriminate) |
| Continuous acoustic flow noise on the service line | Present at the main, decays along the pipe | Present **all the way to the property boundary** — the giveaway |
| Appears only at night / low demand | No | Often yes (a bypassed meter draws whenever supply is on) |
| Found by node fleet | Yes — that's the point | Only if the service line passes a listening node |

The clean discriminator is the last two rows combined, and it is **falsifiable on our existing rig**: an illegal-connection tee on a downstream branch that stays pressurised after the main is shut is physically easy to build with ₹200 of fittings and produces a genuinely different signature from a hole in the main. If we demonstrate that on the rig, the theft claim is earned.

**What we still cannot claim, stated out loud:** that the residual is *specifically* theft rather than meter under-registration. We claim we can bound it, and that the acoustic signature distinguishes a downstream diversion from a main break. Overclaim here and a water-loss specialist ends the conversation.

---

## 5. Why this is defensible against the commercial market

| Existing product category | What it sells | What it cannot do |
|---|---|---|
| Smart water meters + AMI vendors | per-house consumption, billing accuracy, alarms | **No localisation.** Knows a ward lost 150 KL/day, cannot say which street |
| Meter-data analytics platforms (Silverblaze, WEIOT and others — a dozen exist, all commercially mature) | NRW dashboards, benchmark KPIs, consumption analytics | **No physical location of the loss.** The number is the product |
| Acoustic correlators (Sewerin, Goldfish, Mueller — commercial since the 1980s) | accurate leak location, mature | ₹4–15 lakh per listening point, trained operator required, periodic sweeps not continuous |
| Non-physical loss consultants (IWA-certified auditors) | full audit, NRW report, network modelling | **One-off engagement.** ₹3–8 lakh for a study, then it goes stale |
| Our system | continuous monitoring, location to ~10–20 m, NRW in rupees, ₹2,500 per node | — |

**The one-line answer to "this is commercialised":**
> *"The money tells you how much you're losing. The acoustics tell you where to dig. Nobody sells you both — and the meter companies can't add the second half because it needs a different kind of hardware."*

That last clause matters. It is a genuine structural barrier, not a feature we forgot to build: a software analytics company would have to manufacture and deploy acoustic sensor hardware to match us, and our cost position at ₹2,500/node is well below what a services company can charge for a technician with a correlation box.

---

## 6. Revised 4-minute demo script (municipal framing)

Same rig. Same three leaks. Different first 90 seconds and a different final beat. Full rig details in [INNOVATION.md §4](INNOVATION.md).

**0:00–0:45 — the money, before any sensor.**
A slide or a live number: *"Ward 4, 10,000 connections, 50 litres per person per day. That's 500 kilolitres a day into the ward — 15 million litres a month. Your billing system says you sold 350. That gap is 150 kilolitres a day. At ₹180 a kilolitre, that's ₹27,000 a day, ₹9.8 lakh a year. And right now, you cannot tell me which road it's going under."*

> **Assumptions to restate for the actual utility — do not read these numbers aloud as fact.** 10,000 connections · 50 lpcd · 30% NRW · ₹180 per kilolitre (₹0.18 a litre). A household using 5 KL a month at a ₹300 bill implies ~₹60/KL, so realistic municipal tariffs run roughly **₹20–₹200 per kilolitre**. At 150 KL/day of NRW that range gives anything from **₹11 lakh to ₹1.1 crore a year** — the volume figure is stable, the rupee figure is entirely a function of their tariff. Re-run it on their real numbers before the pitch, and if you cannot, quote the litres, not the rupees.

**0:45–1:30 — what you have today, and why it stops.**
Bulk meter + billing data. It reproduces the gap. It has been reproduced by this utility for ten years. Meter replacement is a vendor's recommendation, and it addresses a fraction of the loss.

**1:30–2:15 — leak #1: the loud one.**
Open a 6 mm orifice. Acoustic nodes fire, cross-correlate, and the dashboard puts a pin on the pipe at the known chainage. Judge sees the number: *"87% confidence, 4.2 L/min, 3 metres from the actual hole."* This is the existing capability and it is already verified at 0.1 m average error in simulation.

**2:15–3:00 — the loop closes, in public.**
Close the valve. Bulk flow drops by exactly the leak's rate. Repair. Re-open. `NRW_1 → NRW_2`. **We just measured physical loss, localised it, and proved it, in front of you.** Then: *"The residual, ₹X a year, is what you still don't understand. That's where theft and meter error live. We've narrowed ₹9.8 lakh to a specific address."*

**3:00–3:45 — theft: the rig earns it.**
The illegal-connection tee, downstream branch still live when the main is shut. Close the main valve: the main stops flowing, the branch does not. Acoustic nodes hear flow noise continuing to the property boundary. This is the beat that separates us from every meter-data platform in the market.

**3:45–4:00 — the close.**
*"AquaSentinel is not a better smart meter. It is the ₹2,500 listening node that makes your water-loss number actionable — and the ₹300 pressure sensor that tells you which of your leaks actually let contaminated water in when the pressure dropped."*

---

## 7. Two opening variants — use only one

**Do not present both audiences.** A rural JJM officer and a municipal ward engineer are different buyers with different budgets and different vocabularies. Presenting to both convinces neither. Lead with the money; keep JJM as a deployment line.

**If pitching a municipal utility / NRW track:**
> "You're losing ₹9.8 lakh a year in one ward and you can't tell which road it's under. We tell you which 30 metres to dig, we measure the loss in rupees, and our listening node costs ₹2,500 — less than one truck ride for your crew."

**If pitching the JJM / rural O&M hardware track (deployment line, not a second pitch):**
> "The same node is designed for a 50–100 km rural transmission main where the nearest crew is an hour away and every extra trip costs more than the pipe. We pilot the commercial version in a municipal ward, and the rural version runs on the identical ₹2,500 hardware with solar power."

---

## 8. Questions this framing invites — with the answers

**"Two bulk meters can't tell real loss from apparent loss. Isn't that the whole problem?"**
Yes, and we don't claim otherwise — that's why our rig measures the split as a *difference* before and after repair (§4) instead of inferring it from a single reading. It's the same trick as closing a valve to find a leak.

**"How is this different from the meter-analytics dashboards you're already paying for?"**
They give you the loss in rupees and stop. We give you the loss in rupees *and* the address. Their number tells your board what happened; ours tells your crew what to do on Monday morning.

**"Isn't acoustic leak detection old technology?"**
The technique is old and mature — we're not claiming otherwise. What's new is doing it continuously for ₹2,500 per point instead of ₹4–15 lakh with a trained operator, and folding the result into the water balance so a financial loss and a physical location end up in the same report.

**"What if the utility can't install nodes on private property?"**
They don't need to. Nodes sit on the public road, the main, or the ward boundary — the same places the acoustic correlators sit today. Illegal connections are detected from the main side.

**"How much does this save us?"**
Per pass, it converts an unactionable ward-level number into a work order with an address. The avoided cost is the excavation and the survey trips your crew currently makes to *find* the loss. That saving is what makes a 10–20 m localisation worth paying for — we should compute it honestly for the specific utility before pitching, using their own dig cost, not a number we made up.

---

## 9. What this costs us in build time

| Item | Delta from the existing AquaSentinel plan |
|---|---|
| 2 bulk flow meters + install | +₹8,000, ~2 days of rig work |
| Water-balance computation in the backend | +2 days — night-flow and NRW arithmetic already half-written in §6 of SOLUTION.md |
| Illegal-connection tee + service-line rig branch | +₹300, 1 day |
| "Loss in rupees" dashboard panel | +2 days on the existing PWA |
| Pressure-transient vs acoustic discriminator | +3 days, and it needs a rig re-run to get honest numbers |
| **Total** | **≈ 8–10 days on top of the existing plan** |

If the hardware shipment slips and we need a fallback entry, **this is not the fallback** — the NRW framing depends on physical meters. The groundwater-stress-prediction idea is the fallback, and the reason it is weaker is in [INNOVATION.md §1](INNOVATION.md)'s logic applied to it: published random-forest/LSTM/GRACE models for exactly this already exist, CGWB has issued its own ML guidelines for high-frequency groundwater data, and a colour gradient on a map cannot be distinguished from a random one by a judge.

---

## 10. The claim list — audit-proof

**Claim confidently:**
- The IWA water balance is the standard framework; we apply it, we didn't invent it.
- Existing meter-analytics vendors sell the number, not the location. True and checkable today.
- `NRW_1 − NRW_2` is a *measured* physical loss. It is arithmetic on our own meters.
- Acoustic nodes localise to ~10–20 m; 0.1 m average error in simulation (see [sim_localize.py](sim_localize.py)).
- ₹2,500 per node against ₹4–15 lakh for a commercial correlator.

**Do NOT claim:**
- That we separate theft from meter error. We bound the residual and characterise it. Say it in these words.
- That pressure scaling discriminates theft — it does not, and we put that row in the table ourselves.
- Any rupee figure we invented. Use the utility's own tariff and connection count.
- That we detect pathogens. We detect the negative-pressure windows that permit intrusion ([INNOVATION.md](INNOVATION.md)).
