# Build MeghSentinel SIH 2026 deck IN the official SIH template.
# Rules: never move/delete template shapes; only edit text, add tables/pictures.
import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn

TPL = r"C:\Users\HP\Downloads\SIH2025-IDEA-Presentation-Format.pptx"
OUT_DIR = r"C:\Users\HP\Downloads\code\megh_ppt"
OUT = os.path.join(OUT_DIR, "MeghSentinel-SIH26077-SIH-Idea-Submission.pptx")
os.makedirs(OUT_DIR, exist_ok=True)
GOAT_SRC = r"C:\Users\HP\Downloads\code\sg_imgs\p2_x36_1254x1254.png"
GOAT = r"C:\Users\HP\Downloads\code\sg_logo.png"

NAVY = RGBColor(13, 27, 42)
BLUE = RGBColor(21, 101, 192)
INK = RGBColor(33, 37, 41)
GRAY = RGBColor(90, 100, 110)
WHITE = RGBColor(255, 255, 255)
AMBER = RGBColor(230, 111, 0)

prs = Presentation(TPL)

# --- delete slide 7 (IMPORTANT INSTRUCTIONS) ---
xml_slides = prs.slides._sldIdLst
for sld in list(xml_slides)[6:]:
    xml_slides.remove(sld)

def shp(slide, name):
    for s in slide.shapes:
        if s.name == name:
            return s
    raise KeyError(name)

def set_runs(para, text):
    """Replace paragraph text, keeping run 0's formatting."""
    if para.runs:
        para.runs[0].text = text
        for r in list(para.runs)[1:]:
            r._r.getparent().remove(r._r)
    else:
        r = para.add_run()
        r.text = text

def _strip_bullet(p):
    """Remove the template's auto-bullet so only our own bullet char shows."""
    pPr = p._p.get_or_add_pPr()
    for tag in ("a:buChar", "a:buAutoNum", "a:buNone"):
        for el in pPr.findall(qn(tag)):
            pPr.remove(el)
    bu = pPr.makeelement(qn("a:buNone"), {})
    def_rPr = pPr.find(qn("a:defRPr"))
    if def_rPr is not None:
        def_rPr.addprevious(bu)
    else:
        pPr.append(bu)

def fill_body(shape, items):
    """items: list of (text, size, bold, color, space_after)"""
    tf = shape.text_frame
    tf.word_wrap = True
    tf.clear()
    first = True
    for text, size, bold, color, after in items:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        r = p.add_run()
        r.text = text
        f = r.font
        f.name = "Calibri"
        f.size = Pt(size)
        f.bold = bold
        f.color.rgb = color
        p.space_after = Pt(after)
        p.line_spacing = 0.95
        _strip_bullet(p)

def set_cell(cell, text, size=10.5, bold=False, color=INK, fill=None, align=PP_ALIGN.LEFT):
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    cell.margin_left = Inches(0.06)
    cell.margin_right = Inches(0.06)
    cell.margin_top = Inches(0.02)
    cell.margin_bottom = Inches(0.02)
    if fill is not None:
        cell.fill.solid()
        cell.fill.fore_color.rgb = fill
    tf = cell.text_frame
    tf.word_wrap = True
    tf.clear()
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    f = r.font
    f.name = "Calibri"
    f.size = Pt(size)
    f.bold = bold
    f.color.rgb = color

def add_table(slide, x, y, w, h, rows, hdr=11, body=10.5):
    n_r, n_c = len(rows), len(rows[0])
    gt = slide.shapes.add_table(n_r, n_c, Inches(x), Inches(y), Inches(w), Inches(h))
    t = gt.table
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            if i == 0:
                set_cell(t.cell(i, j), val, size=hdr, bold=True, color=WHITE, fill=NAVY)
            else:
                fillc = RGBColor(240, 244, 251) if i % 2 else WHITE
                set_cell(t.cell(i, j), val, size=body,
                         bold=(j == 0), color=INK, fill=fillc)
    return t

BUL = "\u2022  "

# --- team logo: strip white background, crop to artwork ---
from PIL import Image as _PILImage
_im = _PILImage.open(GOAT_SRC).convert("RGBA")
_im.putdata([(255, 255, 255, 0) if (r > 245 and g > 245 and b > 245) else (r, g, b, a)
             for (r, g, b, a) in _im.getdata()])
_im = _im.crop(_im.getbbox())
_im.save(GOAT)
LOGO_AR = _im.width / _im.height

def goat_in_oval(slide, oval_name):
    """Replace the oval's SCAPEGOATS text with the goat logo image."""
    ov = shp(slide, oval_name)
    for p in ov.text_frame.paragraphs:
        for r in list(p.runs):
            r._r.getparent().remove(r._r)
    ow, oh = Emu(ov.width).inches, Emu(ov.height).inches
    h = oh * 0.84
    w = h * LOGO_AR
    if w > ow * 0.92:
        w = ow * 0.92
        h = w / LOGO_AR
    l = Emu(ov.left).inches + (ow - w) / 2
    t = Emu(ov.top).inches + (oh - h) / 2
    slide.shapes.add_picture(GOAT, Inches(l), Inches(t), Inches(w), Inches(h))

# ============ SLIDE 1 : TITLE ============
s1 = prs.slides[0]
set_runs(shp(s1, "Title 7").text_frame.paragraphs[0], "SMART INDIA HACKATHON 2026")
tb9 = shp(s1, "TextBox 9").text_frame
fields = [
    "Problem Statement ID - SIH26077",
    "Problem Statement Title - AI-Driven Hyper-Local Early Warning System for Severe Weather Nowcasting",
    "Theme - Disaster Management",
    "PS Category - Software",
    "Team ID - (as registered on portal)",
    "Team Name - SCAPEGOATS",
]
for i, val in enumerate(fields, start=1):
    set_runs(tb9.paragraphs[i], val)

# ============ SLIDE 2 : IDEA TITLE ============
s2 = prs.slides[1]
goat_in_oval(s2, "Oval 9")
fill_body(shp(s2, "TextBox 8"), [
    ("MeghSentinel - AI-Driven Hyper-Local Early Warning System for Severe Weather Nowcasting",
     16, True, BLUE, 8),
    (BUL + "Problem: a cloudburst hits with almost no warning - today's weather models are too slow and too broad to see it coming for one district",
     14, False, INK, 5),
    (BUL + "What we built: one AI model that reads satellite images and weather data and tells a district how likely a cloudburst or flash flood is, 2 to 6 hours before it happens",
     14, False, INK, 5),
    (BUL + "How you get the warning: a live risk map that opens on any phone, plus SMS alerts to the districts in danger",
     14, False, INK, 5),
])
add_table(s2, 0.5, 4.1, 7.6, 2.6, [
    ("PROBLEM TODAY", "WITH MEGHSENTINEL"),
    ("Storms intensify within a few hours", "One AI model warns 2 to 6 hours before impact"),
    ("Weather models are too slow and too broad to see a cloudburst", "Reads satellite images directly - no waiting for model runs"),
    ("Too few ground stations, so warnings go untrusted", "District-wise risk map, checked against our own field sensors"),
], hdr=12, body=11.5)
s2.shapes.add_picture(r"C:\Users\HP\Downloads\code\ui_dash.png",
                      Inches(8.4), Inches(4.1), Inches(4.3), Inches(2.69))

# ============ SLIDE 3 : TECHNICAL APPROACH ============
s3 = prs.slides[2]
goat_in_oval(s3, "Oval 10")
fill_body(shp(s3, "TextBox 8"), [
    (BUL + "Inputs - free government data: IMDAA weather grids, INSAT-3D satellite images (MOSDAC) and a terrain map",
     14, False, INK, 3),
    (BUL + "How it works - it learns from past storms: when moisture, heat and wind line up and cloud tops cool quickly, a cloudburst is on the way",
     14, False, INK, 3),
    (BUL + "What you get - a district-wise risk map on a live dashboard plus SMS alerts, 2 to 6 hours before the rain",
     14, False, INK, 3),
    (BUL + "Proof - our own field sensors (rain, pressure, lightning) record what really happened, so every alert can be checked",
     14, False, INK, 3),
])
s3.shapes.add_picture(r"C:\Users\HP\Downloads\code\img_arch.png",
                      Inches(2.5), Inches(4.7), Inches(8.32), Inches(2.15))

# ============ SLIDE 4 : FEASIBILITY AND VIABILITY ============
s4 = prs.slides[3]
goat_in_oval(s4, "Oval 11")
fill_body(shp(s4, "TextBox 8"), [
    (BUL + "Most of the system already exists - our team built and runs the dashboard, the server and the SMS alerts; only the prediction model is new",
     14, False, INK, 4),
    (BUL + "All the data is free - IMDAA and MOSDAC just need a free account, and the terrain maps need no key",
     14, False, INK, 4),
    (BUL + "Plan - idea in October, data and model training in November, a working end-to-end demo in December",
     14, False, INK, 4),
])
add_table(s4, 0.67, 4.4, 12.0, 2.45, [
    ("ASPECT", "STATUS", "EVIDENCE"),
    ("Data", "Confirmed", "Open data from MOSDAC and IMDAA, DEM needs no key"),
    ("Server", "Reused", "The backend service is already live and running"),
    ("Website", "Reused", "The web app installs and shows live sites"),
    ("Alerts", "Reused", "SMS alerts already fire at set thresholds"),
    ("New work", "Scoped", "Prediction model, map layer and node firmware"),
], hdr=11.5, body=11)

# ============ SLIDE 5 : IMPACT AND BENEFITS ============
s5 = prs.slides[4]
goat_in_oval(s5, "Oval 11")
fill_body(shp(s5, "TextBox 8"), [
    (BUL + "2 to 6 extra hours before a cloudburst - enough time to move people out, not just count the damage",
     14, False, INK, 4),
    (BUL + "Warnings name the district, not the whole state, so rescue teams go where the danger actually is",
     14, False, INK, 4),
    (BUL + "Any district can run it on free data, with no expensive licence, and it can be extended to other disasters",
     14, False, INK, 4),
    (BUL + "A public dashboard keeps people informed while the storm is still building, not after it has hit",
     14, False, INK, 4),
])
s5.shapes.add_picture(r"C:\Users\HP\Downloads\code\img_impact.png",
                      Inches(1.17), Inches(4.75), Inches(11.0), Inches(1.83))

# ============ SLIDE 6 : RESEARCH AND REFERENCES ============
s6 = prs.slides[5]
goat_in_oval(s6, "Oval 8")
fill_body(shp(s6, "TextBox 8"), [
    (BUL + "Data sources: IMDAA Reanalysis (IITM + NCEP/NCAR)  |  INSAT-3D/3DR via MOSDAC (mosdac.gov.in)  |  GPM IMERG (gpm.nasa.gov)  |  Copernicus DEM  |  Open-Meteo (open-meteo.com)",
     14, False, INK, 5),
    (BUL + "Method references: Ravuri et al., 'Skilful precipitation nowcasting using deep generative models', Nature (2021)  |  Zhang et al., 'NowcastNet', Science (2023)",
     14, False, INK, 5),
    (BUL + "Problem statement: SIH26077, Ministry of Earth Sciences (MoES) / India Meteorological Department",
     14, False, INK, 5),
    (BUL + "Our platform: the live monitoring dashboard and the field sensor nodes shown on slides 2-3",
     14, False, INK, 5),
])

prs.save(OUT)
print("saved:", OUT)
print("slides:", len(prs.slides.__iter__.__self__._sldIdLst))
