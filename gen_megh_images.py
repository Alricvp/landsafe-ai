# Generate infographics for the MeghSentinel SIH deck
from PIL import Image, ImageDraw, ImageFont

F = r"C:\Windows\Fonts"
def font(name, size):
    return ImageFont.truetype(f"{F}/{name}", size)

H1   = font("segoeuib.ttf", 30)   # column headers
TTL  = font("segoeuib.ttf", 26)     # box titles
TXT  = font("segoeui.ttf", 22)     # body
SM   = font("segoeui.ttf", 19)     # small
B    = font("arialbd.ttf", 24)
BIG  = font("segoeui.ttf", 46)

NAVY = (13, 27, 42)
BLUE = (21, 101, 192)
LBLUE = (227, 242, 253)
AMBER = (230, 111, 0)
ORANGE = (255, 167, 38)
GREEN = (46, 125, 50)
LGREEN = (232, 245, 233)
WHITE = (255, 255, 255)
GRAY = (90, 100, 110)

def rbox(d, xy, fill, outline, w=3, r=14):
    d.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=w)

def center(d, cx, cy, s, f, fill):
    b = d.textbbox((0, 0), s, font=f)
    d.text((cx - (b[2]-b[0])/2 - b[0], cy - (b[3]-b[1])/2 - b[1]), s, font=f, fill=fill)

def arrow(d, x1, y, x2, color=NAVY, w=6):
    d.line([(x1, y), (x2-16, y)], fill=color, width=w)
    d.polygon([(x2, y), (x2-20, y-13), (x2-20, y+13)], fill=color)

# ---------------- architecture diagram (2400 x 620) ----------------
W, H = 2400, 620
im = Image.new("RGB", (W, H), WHITE)
d = ImageDraw.Draw(im)

# column headers
center(d, 280, 34, "DATA SOURCES", H1, BLUE)
center(d, 1020, 34, "AI NOWCAST ENGINE", H1, BLUE)
center(d, 1630, 34, "OUTPUTS", H1, BLUE)
center(d, 2240, 34, "DELIVERY", H1, BLUE)

# col 1: data boxes
data = [
    ("IMDAA Reanalysis", "temperature, humidity, wind profiles"),
    ("INSAT-3D / 3DR (MOSDAC)", "water-vapor + thermal IR channels"),
    ("High-resolution DEM", "slope, basins, terrain channeling"),
    ("Open real-time feeds", "hourly refresh between scenes"),
]
y = 60
for t, s in data:
    rbox(d, (40, y, 520, y+110), LBLUE, NAVY)
    d.text((60, y+14), t, font=TTL, fill=NAVY)
    d.text((60, y+54), s, font=SM, fill=GRAY)
    y += 122

arrow(d, 530, 300, 690)

# col 2: engine
rbox(d, (700, 60, 1340, 555), WHITE, BLUE, w=5)
d.rectangle((702, 62, 1338, 120), fill=NAVY)
center(d, 1020, 91, "Multi-task spatiotemporal DL", TTL, WHITE)
d.text((730, 140), "Shared backbone extracts the 3 storm ingredients:", font=TXT, fill=NAVY)
chips = [
    "MOISTURE  -  IWV accumulation",
    "INSTABILITY  -  CAPE / CIN",
    "LIFT  -  convergence + wind shear",
    "SIGNATURE  -  cloud-top cooling rate",
]
cy = 185
for c in chips:
    rbox(d, (735, cy, 1305, cy+62), LBLUE, BLUE, w=2, r=10)
    center(d, 1020, cy+31, c, SM, NAVY)
    cy += 76
d.text((730, 495), "-> 3 output heads, one unified model", font=TXT, fill=BLUE)

arrow(d, 1350, 300, 1410)

# col 3: hazard chips
haz = [("SEVERE THUNDERSTORM", AMBER), ("CLOUDBURST", (198, 40, 40)), ("FLASH FLOOD", (18, 90, 60))]
y = 80
for t, c in haz:
    rbox(d, (1420, y, 1840, y+145), WHITE, c, w=5)
    d.rectangle((1422, y+2, 1838, y+56), fill=c)
    center(d, 1630, y+29, t, TTL, WHITE)
    center(d, 1630, y+100, "probability map", TXT, NAVY)
    center(d, 1630, y+130, "2 - 6 h lead time", SM, GRAY)
    y += 165

arrow(d, 1850, 300, 1940)

# col 4: delivery
delv = [
    ("FastAPI + WebSocket", "live risk updates as data arrives"),
    ("PWA GIS dashboard", "district risk maps + countdowns"),
    ("Severity SMS alerts", "reach responders without the app"),
]
y = 60
for t, s in delv:
    rbox(d, (1950, y, 2360, y+110), LBLUE, NAVY)
    d.text((1970, y+14), t, font=TTL, fill=NAVY)
    d.text((1970, y+54), s, font=SM, fill=GRAY)
    y += 122

# bottom band: ground-truth nodes
rbox(d, (40, 615-58, 2360, 615), LGREEN, GREEN, w=4)
d.text((70, 575), "ESP32 GROUND-TRUTH NODES", font=TTL, fill=GREEN)
d.text((560, 580), "temp / humidity / pressure / rain / lightning  -  live field validation feeds back into the engine", font=TXT, fill=NAVY)
im.save("img_arch.png")
print("img_arch.png", im.size)

# ---------------- impact chips (2400 x 400) ----------------
W2, H2 = 2400, 400
im2 = Image.new("RGB", (W2, H2), WHITE)
d2 = ImageDraw.Draw(im2)
items = [
    ("2 - 6 HOURS", "actionable lead time before impact"),
    ("DISTRICT-LEVEL", "hyper-local probability risk maps"),
    ("LIVE + SMS", "warnings reach field responders fast"),
    ("OPEN & INDIAN", "indigenous stack, zero licence cost"),
]
cw = (W2 - 5*36) / 4
for i, (a, b) in enumerate(items):
    x = 36 + i*(cw+36)
    rbox(d2, (x, 30, x+cw, 370), WHITE, NAVY, w=4, r=18)
    d2.rounded_rectangle((x+2, 32, x+cw-2, 150), radius=16, fill=NAVY)
    d2.rectangle((x+2, 110, x+cw-2, 150), fill=NAVY)
    center(d2, x+cw/2, 90, a, font("segoeuib.ttf", 44), ORANGE)
    # wrap body text
    words, lines, cur = b.split(), [], ""
    for w_ in words:
        if len(cur + " " + w_) > 22:
            lines.append(cur); cur = w_
        else:
            cur = (cur + " " + w_).strip()
    lines.append(cur)
    for j, ln in enumerate(lines):
        center(d2, x+cw/2, 210 + j*44, ln, TXT, NAVY)
im2.save("img_impact.png")
print("img_impact.png", im2.size)
