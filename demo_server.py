# Serves the REAL terraavani dashboard.html with live + demo data (stdlib only).
import json, os, math, time, datetime, urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

BACKEND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "terraavani-ai", "backend")
PORT = 8014

# ---------- demo sensor history (40 readings, last 2h) ----------
now = datetime.datetime.now()
HISTORY = []
for i in range(40, 0, -1):
    t = now - datetime.timedelta(minutes=i * 3)
    tilt = round(5.5 + (40 - i) * 0.18 + math.sin(i / 3.0) * 0.35, 2)
    moist = round(62.0 + (40 - i) * 0.24, 1)
    status = "warning" if (tilt >= 10.0 or moist >= 60.0) else "safe"
    HISTORY.append({"device_id": "ESP32-NER-001", "tilt": tilt, "moisture": moist,
                    "status": status, "ip": "192.168.1.42", "timestamp": t.isoformat()})

RISK = {"risk_level": "MODERATE", "risk_score": 58.4, "tilt_risk": 41.2, "moisture_risk": 71.3,
        "trend": "increasing",
        "prediction": "\U0001f7e1 Moderate risk. Soil moisture elevated. Monitor closely for changes. \u26a0\ufe0f Risk is INCREASING!",
        "water_density": 1148.0, "avg_tilt": 11.42, "avg_moisture": 70.8,
        "max_tilt": 13.1, "max_moisture": 72.4}

# ---------- NER stations (copied from server.py) ----------
NER = [
    {"id": "ESP32-NER-001", "name": "Gangtok \u2014 32nd Mile NH10 Corridor", "loc": "East Sikkim, Sikkim", "state": "Sikkim", "lat": 27.18, "lng": 88.53, "slope": 42.5},
    {"id": "ESP32-NER-002", "name": "Haflong \u2014 Jatinga Valley Escarpment", "loc": "Dima Hasao, Assam", "state": "Assam", "lat": 25.18, "lng": 93.02, "slope": 38.0},
    {"id": "ESP32-NER-003", "name": "Cherrapunji \u2014 Shella Gorge Rim", "loc": "East Khasi Hills, Meghalaya", "state": "Meghalaya", "lat": 25.30, "lng": 91.70, "slope": 48.0},
    {"id": "ESP32-NER-004", "name": "Guwahati \u2014 Khasi Hills NH6 Section", "loc": "Kamrup, Assam", "state": "Assam", "lat": 26.14, "lng": 91.74, "slope": 35.0},
    {"id": "ESP32-NER-005", "name": "Kohima \u2014 Dimapur NH2 Stretch", "loc": "Kohima, Nagaland", "state": "Nagaland", "lat": 25.67, "lng": 94.11, "slope": 45.0},
    {"id": "ESP32-NER-006", "name": "Aizawl \u2014 Reiek Tlang Ridge", "loc": "Mamit, Mizoram", "state": "Mizoram", "lat": 23.73, "lng": 92.72, "slope": 44.0},
    {"id": "ESP32-NER-007", "name": "Tupul \u2014 Ijei River Rail Corridor", "loc": "Noney, Manipur", "state": "Manipur", "lat": 24.83, "lng": 93.70, "slope": 46.8},
    {"id": "ESP32-NER-008", "name": "Itanagar \u2014 Hollongi Highway Cut", "loc": "Papum Pare, Arunachal", "state": "Arunachal Pradesh", "lat": 27.10, "lng": 93.62, "slope": 40.0},
    {"id": "ESP32-NER-009", "name": "Agartala \u2014 Baramura Hill Range", "loc": "West Tripura, Tripura", "state": "Tripura", "lat": 23.83, "lng": 91.28, "slope": 32.0},
    {"id": "ESP32-NER-010", "name": "Imphal \u2014 Kangchup Road Section", "loc": "Imphal West, Manipur", "state": "Manipur", "lat": 24.82, "lng": 93.94, "slope": 38.0},
]

def _station_risk(rain24, soilmoist, slope):
    rain_risk = min(100.0, (max(rain24, 0.0) / 150.0) * 100.0)
    soil_risk = min(100.0, max(soilmoist, 0.0) * 100.0)
    slope_mult = 1.0 + max((slope - 30.0), 0.0) / 100.0
    score = min(100.0, (rain_risk * 0.45 + soil_risk * 0.55) * slope_mult)
    level = "HIGH" if score >= 65 else ("MODERATE" if score >= 40 else "LOW")
    return round(score, 1), level

_st_cache = {"ts": 0, "data": None}

def fetch_stations():
    if _st_cache["data"] and time.time() - _st_cache["ts"] < 600:
        return _st_cache["data"]
    lats = ",".join(str(s["lat"]) for s in NER)
    lngs = ",".join(str(s["lng"]) for s in NER)
    url = ("https://api.open-meteo.com/v1/forecast"
           f"?latitude={lats}&longitude={lngs}"
           "&current=temperature_2m,relative_humidity_2m,precipitation,weather_code"
           "&hourly=soil_moisture_0_to_1cm"
           "&daily=precipitation_sum,precipitation_probability_max"
           "&past_days=1&forecast_days=3&timezone=Asia%2FKolkata")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TerraavaniAI/1.0"})
        payload = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
        results = payload if isinstance(payload, list) else [payload]
    except Exception as e:
        print("[stations] Open-Meteo failed:", e)
        return _st_cache["data"] or []
    out = []
    for st, wx in zip(NER, results):
        try:
            daily = wx.get("daily", {}).get("precipitation_sum", []) or [0.0, 0.0]
            rain24 = round(sum(x or 0.0 for x in daily[:2]), 1)
            sm = wx.get("hourly", {}).get("soil_moisture_0_to_1cm", []) or []
            soil = sm[-1] if sm else 0.0
            cur = wx.get("current", {}) or {}
            score, level = _station_risk(rain24, soil, st["slope"])
            tilt_est = round((score / 100.0) * 1.8, 2)
            daily_rain = wx.get("daily", {}).get("precipitation_sum", []) or []
            daily_prob = wx.get("daily", {}).get("precipitation_probability_max", []) or []
            daily_times = wx.get("daily", {}).get("time", []) or []
            forecast = []
            for i in range(2, min(4, len(daily_rain))):
                fr = max(daily_rain[i] or 0.0, 0.0)
                fs, fl = _station_risk(fr, soil, st["slope"])
                forecast.append({"day": ("Tomorrow", "Day After")[i - 2],
                                 "date": daily_times[i] if i < len(daily_times) else "",
                                 "rain": round(fr, 1),
                                 "prob": daily_prob[i] if i < len(daily_prob) else None,
                                 "score": fs, "level": fl})
            out.append({**st, "rain": rain24, "moisture": round(soil * 100.0, 1),
                        "temperature": cur.get("temperature_2m"),
                        "humidity": cur.get("relative_humidity_2m"),
                        "weather_code": cur.get("weather_code"),
                        "tilt": tilt_est, "score": score, "level": level,
                        "forecast": forecast})
        except Exception as e:
            print("[stations] parse failed:", e)
    if out:
        _st_cache["ts"] = time.time()
        _st_cache["data"] = out
    return out or []

HIST_SUMMARY = None
def historical_payload():
    global HIST_SUMMARY
    with open(os.path.join(BACKEND, "historical.json"), encoding="utf-8") as f:
        data = json.load(f)
    if HIST_SUMMARY is None:
        total_deaths = sum(d.get("deaths", 0) for d in data)
        years = sorted(set(d.get("year", 0) for d in data))
        HIST_SUMMARY = {"total_incidents": len(data), "total_deaths": total_deaths,
                        "years_covered": f"{years[0]}-{years[-1]}" if years else "N/A"}
    return {"data": data, "summary": HIST_SUMMARY}

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            # bootstrap: pre-select a region so the dashboard opens past the modal
            boot = (b"<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>"
                    b"<script>try{sessionStorage.setItem('terraavani-region','Assam');"
                    b"location.replace('/app');}catch(e){location.replace('/app');}</script>"
                    b"</body></html>")
            self._send(200, boot, "text/html; charset=utf-8")
        elif p == "/app":
            with open(os.path.join(BACKEND, "dashboard.html"), "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        elif p in ("/sw.js", "/manifest.json"):
            try:
                with open(os.path.join(BACKEND, p.lstrip("/")), "rb") as f:
                    ct = "application/javascript" if p.endswith(".js") else "application/manifest+json"
                    self._send(200, f.read(), ct)
            except OSError:
                self._send(404, b"{}", "text/plain")
        elif p == "/api/latest":
            self._send(200, json.dumps({"data": HISTORY[-1], "risk": RISK}).encode())
        elif p == "/api/history":
            self._send(200, json.dumps({"data": HISTORY}).encode())
        elif p == "/api/risk":
            self._send(200, json.dumps({"data": RISK}).encode())
        elif p == "/api/stations":
            data = fetch_stations()
            self._send(200, json.dumps({"data": data, "source": "open-meteo"}).encode())
        elif p == "/api/reports":
            self._send(200, json.dumps({"data": []}).encode())
        elif p == "/api/historical":
            self._send(200, json.dumps(historical_payload()).encode())
        elif p == "/api/sms/recipients":
            self._send(200, json.dumps({"recipients": []}).encode())
        elif p == "/health":
            self._send(200, json.dumps({"status": "ok"}).encode())
        else:
            self._send(404, b"{}", "text/plain")

if __name__ == "__main__":
    print(f"demo dashboard: http://127.0.0.1:{PORT}/")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
