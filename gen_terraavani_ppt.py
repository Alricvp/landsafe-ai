# Build Terraavani AI SIH 2026 deck - truthful content version (8 slides, 16:9)
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import os

NAVY  = RGBColor(13, 27, 42)
INK   = RGBColor(33, 37, 41)
GREEN = RGBColor(27, 94, 32)
TEAL  = RGBColor(0, 121, 107)
LTEAL = RGBColor(178, 223, 219)
LIGHT = RGBColor(240, 244, 241)
AMBER = RGBColor(230, 126, 34)
RED   = RGBColor(176, 58, 46)
GRAY  = RGBColor(110, 118, 125)
WHITE = RGBColor(255, 255, 255)
LRED  = RGBColor(253, 237, 236)
LGRN  = RGBColor(233, 245, 233)

prs = Presentation()
prs.slide_width  = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
W, H = 13.333, 7.5

def rect(slide, x, y, w, h, fill, line=None, shape=MSO_SHAPE.RECTANGLE):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line; s.line.width = Pt(1)
    s.shadow.inherit = False
    return s

def txt(slide, x, y, w, h, paras, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    first = True
    for p in paras:
        para = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        para.alignment = p.get("align", align)
        if p.get("space_before"): para.space_before = Pt(p["space_before"])
        if p.get("space_after"):  para.space_after  = Pt(p["space_after"])
        if p.get("line"):         para.line_spacing = p["line"]
        for r in p["runs"]:
            run = para.add_run(); run.text = r[0]
            f = run.font
            f.name = r[1].get("font", "Calibri")
            f.size = Pt(r[1].get("size", 14))
            f.bold = r[1].get("bold", False)
            f.italic = r[1].get("italic", False)
            f.color.rgb = r[1].get("color", INK)
    return tb

def P(text, size=14, bold=False, color=INK, align=PP_ALIGN.LEFT, space_after=6, italic=False, font="Calibri", line=None):
    d = {"runs": [(text, {"size": size, "bold": bold, "color": color, "italic": italic, "font": font})],
         "align": align, "space_after": space_after}
    if line: d["line"] = line
    return d

def chip(slide, x, y, w, h, text, fill, tcolor=WHITE, size=13, bold=True):
    rect(slide, x, y, w, h, fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(slide, x, y, w, h, [P(text, size=size, bold=bold, color=tcolor, align=PP_ALIGN.CENTER, space_after=0)],
        anchor=MSO_ANCHOR.MIDDLE)

def title_bar(slide, title, num):
    rect(slide, 0, 0, W, 1.0, NAVY)
    rect(slide, 0, 1.0, W, 0.06, TEAL)
    txt(slide, 0.5, 0.12, 11.5, 0.8, [P(title, size=28, bold=True, color=WHITE)], anchor=MSO_ANCHOR.MIDDLE)
    txt(slide, 12.35, 0.12, 0.8, 0.8, [P(num, size=20, bold=True, color=LTEAL, align=PP_ALIGN.RIGHT)],
        anchor=MSO_ANCHOR.MIDDLE)
    txt(slide, 0.5, 7.08, 12.3, 0.35,
        [P("SIH 2026  |  Team Scapegoats  |  PS SIH26178  |  Terraavani AI", size=10, color=GRAY)])

def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text

# ---------------- SLIDE 1 : TITLE ----------------
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, W, H, NAVY)
rect(s, 0, 0, 0.32, H, GREEN)
rect(s, 0.32, 0, 0.10, H, TEAL)
txt(s, 1.0, 0.75, 11.3, 0.5, [P("S M A R T   I N D I A   H A C K A T H O N   2 0 2 6", size=16, bold=True, color=LTEAL, align=PP_ALIGN.CENTER)])
txt(s, 1.0, 1.55, 11.3, 1.3, [P("TERRAAVANI AI", size=60, bold=True, color=WHITE, align=PP_ALIGN.CENTER)])
txt(s, 1.0, 2.85, 11.3, 0.6, [P("A resilient, AI-powered Environmental Intelligence Network", size=22, color=LTEAL, align=PP_ALIGN.CENTER)])
txt(s, 1.0, 3.45, 11.3, 0.5, [P("Early detection  -  Localized edge intelligence  -  Actionable multi-hazard alerts", size=15, color=RGBColor(200, 214, 224), align=PP_ALIGN.CENTER)])
txt(s, 1.0, 3.95, 11.3, 0.45, [P("\"Enabling authorities and communities to shift from reactive disaster response to proactive risk prevention.\"",
    size=13, italic=True, color=RGBColor(160, 180, 195), align=PP_ALIGN.CENTER)])
c1y = 4.85
chip(s, 1.30, c1y, 2.55, 0.62, "PS ID:  SIH26178", RGBColor(23, 42, 63), LTEAL)
chip(s, 4.05, c1y, 2.90, 0.62, "Theme: Disaster Mgmt", RGBColor(23, 42, 63), LTEAL)
chip(s, 7.15, c1y, 2.30, 0.62, "Category: Hardware", RGBColor(23, 42, 63), LTEAL)
chip(s, 9.65, c1y, 2.35, 0.62, "Team: SCAPEGOATS", GREEN, WHITE)
txt(s, 1.0, 5.75, 11.3, 0.4, [P("Team ID: ____________________     Team Leader: ____________________", size=14, color=RGBColor(200, 214, 224), align=PP_ALIGN.CENTER)])
txt(s, 1.0, 6.65, 11.3, 0.4, [P("Problem Statement by: Sarim Moin  -  Qualcomm Inc  -  Ministry of Education's Innovation Cell (MIC)",
    size=11, color=RGBColor(140, 160, 175), align=PP_ALIGN.CENTER)])
notes(s, "Terraavani = Terra (Latin) + Avani (Sanskrit), both mean Earth. One line: a solar-powered edge-AI sensor network that detects floods, fires, pollution, heat and landslide risk on the node itself and alerts authorities before disasters escalate.")

# ---------------- SLIDE 2 : IDEA / SOLUTION ----------------
s = prs.slides.add_slide(BLANK)
title_bar(s, "IDEA  -  PROPOSED SOLUTION", "2")
txt(s, 0.5, 1.35, 7.4, 0.5, [P("What we are building  (working prototype in our GitHub)", size=18, bold=True, color=GREEN)])
bl = [
    ("Solar ESP32 sensor nodes", " on vulnerable slopes - tilt, vibration and soil saturation sampled every 2 seconds."),
    ("Edge AI on the node", " median-of-9 filtering + auto-calibration; risk classified on the ESP32 with zero internet - survives network outages."),
    ("Only alerts travel", " compact readings and risk alerts to the cloud - minimal latency, minimal bandwidth, as the PS demands."),
    ("Sensor + satellite fusion", " live GloFAS river discharge (flood), CAMS PM2.5/PM10 (pollution), temperature maxima (heat); NASA FIRMS fire next."),
    ("Actionable output", " live risk map of 10 NE cities + push/siren/vibration alerts in 5 languages (EN/HI/AS/BN/MN)."),
]
paras = []
for head, rest in bl:
    paras.append({"runs": [("\u25AA  ", {"size": 15, "color": TEAL, "bold": True}),
                           (head, {"size": 15, "bold": True, "color": INK}),
                           (rest, {"size": 15, "color": INK})], "space_after": 12, "line": 1.05})
txt(s, 0.5, 1.95, 7.4, 4.3, paras)
rect(s, 0.5, 6.25, 7.4, 0.62, LGRN, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, 0.7, 6.25, 7.0, 0.62, [P("Verified live: Silchar river discharge 1338.7 m3/s - real GloFAS satellite data.",
    size=12.5, bold=True, color=GREEN)], anchor=MSO_ANCHOR.MIDDLE)
rect(s, 8.25, 1.35, 4.55, 5.45, LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, 8.5, 1.55, 4.05, 0.5, [P("MULTI-HAZARD COVERAGE", size=15, bold=True, color=GREEN, align=PP_ALIGN.CENTER)])
haz = [("Floods & flash floods", TEAL), ("Forest fires & smoke", AMBER), ("Hazardous air pollution (PM2.5 / PM10)", RGBColor(120, 90, 140)),
       ("Extreme heat conditions", RED), ("Landslide precursors", RGBColor(110, 80, 60)), ("Industrial gas / chemical leaks", GRAY),
       ("Water quality degradation", RGBColor(0, 105, 146))]
yy = 2.15
for htxt, hcol in haz:
    chip(s, 8.5, yy, 4.05, 0.58, htxt, hcol, WHITE, size=12.5, bold=True)
    yy += 0.67
notes(s, "Every point is already working: node firmware, FastAPI backend and PWA dashboard are on GitHub; the multi-hazard engine for 10 NE cities is live on free keyless APIs.")

# ---------------- SLIDE 3 : HARDWARE ----------------
s = prs.slides.add_slide(BLANK)
title_bar(s, "HARDWARE  -  WHAT WE ACTUALLY USE", "3")
def bom_table(slide, x, y, w, rows, title, tcol):
    txt(slide, x, y - 0.42, w, 0.4, [P(title, size=14.5, bold=True, color=tcol)])
    tbl = slide.shapes.add_table(len(rows), 2, Inches(x), Inches(y), Inches(w), Inches(0.28 * len(rows))).table
    tbl.columns[0].width = Inches(w * 0.72); tbl.columns[1].width = Inches(w * 0.28)
    for i, (a, b) in enumerate(rows):
        ca, cb = tbl.cell(i, 0), tbl.cell(i, 1)
        ca.text = a; cb.text = b
        hdr = (i == 0); tot = (i == len(rows) - 1)
        for c in (ca, cb):
            c.margin_left = Inches(0.06); c.margin_top = Inches(0.01); c.margin_bottom = Inches(0.01)
            pr = c.text_frame.paragraphs[0]
            pr.font.size = Pt(11); pr.font.bold = hdr or tot
            pr.font.color.rgb = WHITE if (hdr or tot) else INK
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
        for c, col in ((ca, NAVY if hdr else (GREEN if tot else (LIGHT if i % 2 else WHITE))), (cb, NAVY if hdr else (GREEN if tot else (LIGHT if i % 2 else WHITE)))):
            c.fill.solid(); c.fill.fore_color.rgb = col
built = [("Component", "Cost (Rs)"), ("ESP32 DevKit (Wi-Fi MCU)", "350"),
         ("MPU-6500 tilt + vibration", "150"), ("Capacitive soil moisture", "120"),
         ("0.96\" SSD1306 OLED", "180"), ("Solar 6V + TP4056 + 18650", "330"),
         ("IP65 enclosure + wiring", "250"), ("Misc (headers, perfboard)", "420"),
         ("BUILT NODE TOTAL", "1,800")]
addons = [("Add-on sensor", "Cost (Rs)"), ("HC-SR04 water level (flood)", "50"),
          ("DHT22 temp + humidity (heat)", "250"), ("MQ-135 gas (industrial leak)", "150"),
          ("FULL NODE", "~2,250")]
bom_table(s, 0.5, 1.95, 5.9, built, "A. BUILT & WORKING NODE (landslide)", GREEN)
bom_table(s, 6.85, 1.95, 5.9, addons, "B. MULTI-HAZARD ADD-ONS (next build)", AMBER)
rect(s, 6.85, 3.65, 5.9, 1.55, LGRN, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, 7.05, 3.78, 5.5, 1.35,
    [P("NO Rs 40,000 PM sensor needed:", size=13, bold=True, color=GREEN),
     P("PM2.5/PM10 and river discharge come FREE from Copernicus CAMS and GloFAS satellites via API - the hybrid edge+cloud advantage.", size=12, line=1.05)])
rect(s, 0.5, 5.85, 12.3, 0.85, RGBColor(253, 237, 236), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, 0.8, 5.85, 11.8, 0.85,
    [P("Commercial monitoring stations: Rs 3-20 lakh each.  Terraavani node: Rs 1,800-2,250, solar powered - ~100x cheaper, so dense networks become affordable.",
       size=13.5, bold=True, color=RED)], anchor=MSO_ANCHOR.MIDDLE)
notes(s, "Category is HARDWARE: the node on the left is fully assembled and running. Add-ons are off-the-shelf Indian components. Satellite data replaces the most expensive sensors.")

# ---------------- SLIDE 4 : TECHNICAL APPROACH ----------------
s = prs.slides.add_slide(BLANK)
title_bar(s, "TECHNICAL APPROACH  -  ACTUAL STACK", "4")
flow = [("ESP32 NODE", "MPU-6500 + soil + OLED", NAVY), ("FASTAPI BACKEND", "risk engine on Render", GREEN),
        ("HAZARD ENGINE", "10 NE cities, satellite", TEAL), ("WEBSOCKET /ws", "real-time push", RGBColor(0, 105, 146)),
        ("PWA DASHBOARD", "map + alerts, 5 languages", AMBER)]
fx = 0.5; fw = 2.30; gap = 0.32
for i, (t1, t2, col) in enumerate(flow):
    chip(s, fx, 1.45, fw, 0.95, t1 + "\n" + t2, col, WHITE, size=11.5, bold=True)
    if i < len(flow) - 1:
        txt(s, fx + fw - 0.02, 1.45, gap + 0.06, 0.95, [P("\u25B6", size=16, bold=True, color=GRAY, align=PP_ALIGN.CENTER)], anchor=MSO_ANCHOR.MIDDLE)
    fx += fw + gap
cards = [
    ("FIRMWARE (Arduino C++)", ["Median-of-9 filter, 500-sample auto-calibration", "Tilt thresholds: 10 deg warn / 60 deg danger", "Moisture: 60% / 80%; posts every 2 s", "OLED status display, works offline"], GREEN),
    ("BACKEND (Python)", ["FastAPI 0.115 + Uvicorn + WebSockets 12.0", "Risk = rain 45% + soil 55% x slope factor", "10-min cache on satellite API calls", "REST + WebSocket, Render free tier"], TEAL),
    ("LIVE DATA APIs", ["Open-Meteo Flood API (GloFAS discharge)", "Open-Meteo Air Quality (CAMS PM2.5/PM10)", "Open-Meteo Forecast (rain, heat)", "NASA FIRMS fire - integration next"], RGBColor(0, 105, 146)),
    ("FRONTEND (PWA)", ["Vanilla JS single-page, service worker offline", "Leaflet GIS + ArcGIS satellite tiles", "Web Audio siren + Vibration API + push", "5 languages: EN/HI/AS/BN/MN"], RGBColor(90, 70, 140)),
    ("CLOUD-EDGE HYBRID", ["Edge decides in seconds, even offline", "Cloud: forecasting, trends, policy support", "Only alert packets on the network", "Free-tier hosting, zero licence cost"], RED),
    ("SCALABILITY", ["Wi-Fi today; LoRaWAN / NB-IoT designed-in", "Same node, different sensor mix per hazard", "Village pilot to state-wide rollout", "1,000 nodes ~ Rs 22 lakh"], AMBER),
]
cw, ch = 4.05, 2.15; gx, gy = 0.5, 2.75
for i, (head, items, col) in enumerate(cards):
    cx = gx + (i % 3) * (cw + 0.20); cy = gy + (i // 3) * (ch + 0.18)
    rect(s, cx, cy, cw, ch, WHITE, line=col, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(s, cx, cy, cw, 0.42, col, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, cx, cy, cw, 0.42, [P(head, size=13, bold=True, color=WHITE, align=PP_ALIGN.CENTER)], anchor=MSO_ANCHOR.MIDDLE)
    paras = [{"runs": [("\u2022 ", {"size": 11, "color": col, "bold": True}), (it, {"size": 11})], "space_after": 2} for it in items]
    txt(s, cx + 0.15, cy + 0.5, cw - 0.3, ch - 0.6, paras)
notes(s, "This maps 1:1 to the PS expected solution: distributed nodes, on-device AI, multi-hazard alerts, risk mapping, notifications, hybrid architecture, scalable protocols.")

# ---------------- SLIDE 5 : FEASIBILITY ----------------
s = prs.slides.add_slide(BLANK)
title_bar(s, "FEASIBILITY AND VIABILITY", "5")
pairs = [
    ("No connectivity in remote forests / hills",
     "Edge AI decides on the node itself; OLED shows status on-site; readings sync when network returns; LoRaWAN module (Rs 300) designed in."),
    ("No grid power in remote deployments",
     "Already solved: 6V solar + TP4056 + 18650 with deep-sleep duty cycles - months of unattended, grid-free operation."),
    ("False alarms destroy public trust",
     "Median-of-9 filtering kills sensor noise; two-level thresholds; tiered Watch/Warning/Danger alerts with confidence, not raw guesses."),
    ("Cost of scaling to a state-wide network",
     "Rs 2,250/node; free satellite data (GloFAS, CAMS, FIRMS, Open-Meteo); free Render hosting - 1,000 nodes ~ Rs 22 lakh vs Rs 300+ crore commercial."),
]
yy = 1.45
for ch_t, so_t in pairs:
    rect(s, 0.5, yy, 5.55, 1.22, LRED, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(s, 0.5, yy, 0.14, 1.22, RED)
    txt(s, 0.78, yy + 0.08, 5.15, 1.1,
        [P("CHALLENGE", size=10.5, bold=True, color=RED), P(ch_t, size=13, bold=True, color=INK, space_after=0)], anchor=MSO_ANCHOR.MIDDLE)
    txt(s, 6.15, yy + 0.28, 0.8, 0.7, [P("\u2192", size=24, bold=True, color=GRAY, align=PP_ALIGN.CENTER)], anchor=MSO_ANCHOR.MIDDLE)
    rect(s, 6.95, yy, 5.9, 1.22, LGRN, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(s, 6.95, yy, 0.14, 1.22, GREEN)
    txt(s, 7.23, yy + 0.08, 5.5, 1.1,
        [P("SOLUTION", size=10.5, bold=True, color=GREEN), P(so_t, size=12, color=INK, space_after=0, line=1.0)], anchor=MSO_ANCHOR.MIDDLE)
    yy += 1.40
notes(s, "Each answer is engineered into the prototype, not hand-waved: offline edge decisions, solar power, filtered tiered alerts, and a BOM cheap enough for dense deployment.")

# ---------------- SLIDE 6 : IMPACT ----------------
s = prs.slides.add_slide(BLANK)
title_bar(s, "IMPACT AND BENEFITS", "6")
tiles = [
    ("Lives saved", "Minutes-to-hours earlier warnings for floods, fires, landslides - real evacuation time for communities.", RED),
    ("Hyperlocal intelligence", "Dense Rs 2,250 nodes fill the gaps between sparse IMD / NDMA / CWC stations - village-level, not district-level.", GREEN),
    ("For authorities", "Live 10-corridor risk map, prioritized confidence-scored alerts, REST API ready for SDMA / NDMA dashboards.", TEAL),
    ("For citizens", "Free PWA on any phone - no app store, 5 Indian languages, siren + vibration alerts even on silent mode.", RGBColor(0, 105, 146)),
    ("Economy & environment", "Protects homes, roads, crops and forests; earlier fire detection protects carbon sinks and air quality.", RGBColor(110, 80, 60)),
    ("Made for India", "Off-the-shelf Indian components, solar power, one district pilot scales to state-wide rollout.", AMBER),
]
cw, ch = 4.05, 2.30; gx, gy = 0.5, 1.5
for i, (head, body, col) in enumerate(tiles):
    cx = gx + (i % 3) * (cw + 0.20); cy = gy + (i // 3) * (ch + 0.22)
    rect(s, cx, cy, cw, ch, LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    rect(s, cx, cy, cw, 0.50, col, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    txt(s, cx, cy, cw, 0.50, [P(head, size=14, bold=True, color=WHITE, align=PP_ALIGN.CENTER)], anchor=MSO_ANCHOR.MIDDLE)
    txt(s, cx + 0.18, cy + 0.62, cw - 0.36, ch - 0.75, [P(body, size=12, color=INK, line=1.05)])
notes(s, "Tie back to the PS goal: shift from reactive response to proactive prevention. Authorities get decision support; citizens get actionable warnings in their own language.")

# ---------------- SLIDE 7 : STATUS & ROADMAP ----------------
s = prs.slides.add_slide(BLANK)
title_bar(s, "CURRENT STATUS AND ROADMAP", "7")
txt(s, 0.5, 1.35, 5.9, 0.5, [P("DONE - working today", size=16, bold=True, color=GREEN)])
done = [
    "Landslide sensor node assembled: ESP32 + MPU-6500 + soil moisture + OLED, solar powered",
    "Edge firmware: auto-calibration, median filter, on-device risk, offline OLED status",
    "FastAPI backend on Render: risk engine + WebSocket real-time stream",
    "Multi-hazard engine live for 10 NE cities: flood (GloFAS), pollution (CAMS), heat",
    "PWA dashboard: GIS risk map, siren + vibration + push alerts, 5 languages, offline mode",
    "Verified live satellite data (Silchar 1338.7 m3/s via GloFAS)",
]
paras = [{"runs": [("\u2713  ", {"size": 13.5, "color": GREEN, "bold": True}), (d, {"size": 13})], "space_after": 10, "line": 1.05} for d in done]
txt(s, 0.5, 1.95, 5.9, 4.8, paras)
rect(s, 6.8, 1.35, 6.0, 5.3, LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, 7.1, 1.5, 5.4, 0.5, [P("NEXT - funded by the BOM", size=16, bold=True, color=AMBER)])
nxt = [
    ("2-4 weeks:", " NASA FIRMS fire detection into the hazard engine"),
    ("2-4 weeks:", " add-on sensors: HC-SR04 water level, DHT22, MQ-135 (~Rs 450/node)"),
    ("2-4 weeks:", " TinyML anomaly model on the ESP32"),
    ("2-3 months:", " LoRaWAN backend for zero-network zones"),
    ("2-3 months:", " district pilot with SDMA; water-quality sensor variant"),
]
paras = []
for head, rest in nxt:
    paras.append({"runs": [("\u25B8 ", {"size": 13.5, "color": AMBER, "bold": True}),
                           (head, {"size": 13, "bold": True}), (rest, {"size": 13})], "space_after": 12, "line": 1.05})
txt(s, 7.1, 2.1, 5.5, 3.4, paras)
chip(s, 7.1, 5.75, 5.4, 0.62, "Same node, same brain - only the sensor mix changes", TEAL, WHITE, size=13)
notes(s, "Be honest with judges: landslide node + flood/pollution/heat engine are live; fire, extra sensors and TinyML are the funded next steps. This slide shows execution speed.")

# ---------------- SLIDE 8 : REFERENCES ----------------
s = prs.slides.add_slide(BLANK)
title_bar(s, "RESEARCH AND REFERENCES", "8")
txt(s, 0.5, 1.35, 5.9, 0.5, [P("Live data sources we use (all keyless / open)", size=16, bold=True, color=GREEN)])
srcs = [
    ("Open-Meteo Forecast API", " - rainfall & heat outlook"),
    ("Open-Meteo Flood API", " - GloFAS river discharge forecasts"),
    ("Open-Meteo Air Quality API", " - Copernicus CAMS PM2.5 / PM10 / AQI"),
    ("NASA FIRMS", " - near-real-time active fire detections (next)"),
    ("ISRO / NRSC", " - Landslide Atlas of India"),
    ("IMD / NDMA / SDMA", " - disaster reports & thresholds"),
]
paras = []
for head, rest in srcs:
    paras.append({"runs": [("\u25AA  ", {"size": 14, "color": TEAL, "bold": True}),
                           (head, {"size": 14, "bold": True}), (rest, {"size": 14})], "space_after": 12, "line": 1.05})
txt(s, 0.5, 1.95, 5.9, 4.6, paras)
rect(s, 6.8, 1.35, 6.0, 5.3, LIGHT, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
txt(s, 7.1, 1.5, 5.4, 0.5, [P("REFERENCES", size=16, bold=True, color=GREEN)])
refs = [
    "[1] NDMA - National Disaster Management Plan & Guidelines",
    "[2] ISRO-NRSC - Landslide Atlas of India, 2023",
    "[3] ECMWF / Copernicus - GloFAS: Global Flood Awareness System",
    "[4] Copernicus CAMS - Regional Air Quality Production System",
    "[5] NASA FIRMS - NRT Active Fire & Thermal Anomaly Data (VIIRS/MODIS)",
    "[6] Open-Meteo - Open-source numerical weather & climate APIs",
    "[7] Qualcomm - Edge AI / TinyML deployment whitepapers",
]
paras = [P(r, size=12.5, space_after=10) for r in refs]
txt(s, 7.1, 2.1, 5.5, 4.4, paras)
notes(s, "All live APIs are keyless and free - the demo works end-to-end today. Node hardware validates the HARDWARE category; satellite fusion validates the intelligence layer.")

out = os.path.join(os.path.expanduser("~"), "Desktop", "Terraavani-AI-SIH2026.pptx")
prs.save(out)
print("saved:", out, "| slides: 8")
