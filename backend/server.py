"""
Landsafe AI - Backend Server
Receives tilt + moisture data from ESP32, serves the public dashboard.
Includes landslide prediction, weather data, and map.
Deploy to Render for a permanent public URL.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import os
import math
import base64
import uuid
import urllib.request
import urllib.parse

app = FastAPI(title="Landsafe AI", version="3.0.0")

# Allow all origins for public access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- In-memory store (last 500 readings) ----
sensor_data = []
MAX_READINGS = 500
citizen_reports = []
MAX_REPORTS = 200

# ---- Connected WebSocket clients ----
connected_clients: list[WebSocket] = []

# ---- Data model ----
class TiltReading(BaseModel):
    device_id: str
    tilt: float
    status: str
    ip: str = ""
    moisture: float = 0.0

# ---- Citizen report data model ----
class CitizenReport(BaseModel):
    report_type: str  # crack, slope_damage, blocked_road, flooding, other
    severity: str     # low, medium, high, critical
    lat: float
    lng: float
    description: str = ""
    reporter_name: str = "Anonymous"
    photo_data: str = ""  # base64 encoded image

class SMSAlert(BaseModel):
    phone: str
    message: str
    severity: str = "info"

class WhatsAppAlert(BaseModel):
    phone: str
    message: str
    severity: str = "info"



# ---- Helper: calculate landslide risk ----
def calculate_risk(readings):
    """Calculate landslide risk based on recent tilt + moisture data."""
    if not readings:
        return {
            "risk_level": "LOW",
            "risk_score": 0,
            "tilt_risk": 0,
            "moisture_risk": 0,
            "trend": "stable",
            "prediction": "No landslide risk detected.",
            "water_density": 0,
        }

    recent = readings[-20:]  # Last 20 readings

    # Average tilt
    avg_tilt = sum(r.get("tilt", 0) for r in recent) / len(recent)
    max_tilt = max(r.get("tilt", 0) for r in recent)

    # Average moisture
    avg_moisture = sum(r.get("moisture", 0) for r in recent) / len(recent)
    max_moisture = max(r.get("moisture", 0) for r in recent)

    # Water density (kg/m^3 estimate from moisture %)
    # Soil density ~1600 kg/m^3, water adds weight
    water_density = 1000 + (avg_moisture / 100.0) * 600  # 1000-1600 range

    # Tilt risk (0-100)
    tilt_risk = min(100, (avg_tilt / 45.0) * 100)

    # Moisture risk (0-100)
    moisture_risk = min(100, (avg_moisture / 90.0) * 100)

    # Combined risk score
    # Moisture amplifies tilt risk (wet soil slides more easily)
    moisture_multiplier = 1.0 + (avg_moisture / 100.0) * 0.5
    risk_score = min(100, (tilt_risk * 0.6 + moisture_risk * 0.4) * moisture_multiplier)

    # Trend detection
    if len(readings) >= 10:
        old_avg_tilt = sum(r.get("tilt", 0) for r in readings[-20:-10]) / min(10, len(readings[-20:-10]))
        new_avg_tilt = sum(r.get("tilt", 0) for r in readings[-10:]) / min(10, len(readings[-10:]))
        if new_avg_tilt > old_avg_tilt * 1.2:
            trend = "increasing"
        elif new_avg_tilt < old_avg_tilt * 0.8:
            trend = "decreasing"
        else:
            trend = "stable"
    else:
        trend = "stable"

    # Risk level
    if risk_score >= 70 or (avg_tilt >= 40 and avg_moisture >= 70):
        risk_level = "CRITICAL"
        prediction = "⚠️ HIGH landslide probability! Ground unstable with saturated soil. Evacuate immediately!"
    elif risk_score >= 50 or (avg_tilt >= 30 and avg_moisture >= 60):
        risk_level = "HIGH"
        prediction = "🔴 Significant landslide risk. Heavy rain + tilt detected. Prepare for evacuation."
    elif risk_score >= 30 or avg_moisture >= 60:
        risk_level = "MODERATE"
        prediction = "🟡 Moderate risk. Soil moisture elevated. Monitor closely for changes."
    elif risk_score >= 15:
        risk_level = "LOW-MODERATE"
        prediction = "🟢 Minor risk detected. Normal monitoring recommended."
    else:
        risk_level = "LOW"
        prediction = "✅ Low risk. Conditions stable."

    if trend == "increasing":
        prediction += " ⚠️ Risk is INCREASING!"

    return {
        "risk_level": risk_level,
        "risk_score": round(risk_score, 1),
        "tilt_risk": round(tilt_risk, 1),
        "moisture_risk": round(moisture_risk, 1),
        "trend": trend,
        "prediction": prediction,
        "water_density": round(water_density, 1),
        "avg_tilt": round(avg_tilt, 2),
        "avg_moisture": round(avg_moisture, 1),
        "max_tilt": round(max_tilt, 2),
        "max_moisture": round(max_moisture, 1),
    }


# ---- REST endpoint for ESP32 ----
@app.post("/api/tilt")
async def receive_tilt(reading: TiltReading):
    entry = {
        "device_id": reading.device_id,
        "tilt": reading.tilt,
        "moisture": reading.moisture,
        "status": reading.status,
        "ip": reading.ip,
        "timestamp": datetime.now().isoformat(),
    }

    sensor_data.append(entry)
    if len(sensor_data) > MAX_READINGS:
        sensor_data.pop(0)

    # Broadcast to dashboard clients
    message = json.dumps({"type": "sensor", "data": entry})
    disconnected = []
    for client in connected_clients:
        try:
            await client.send_text(message)
        except:
            disconnected.append(client)
    for client in disconnected:
        connected_clients.remove(client)

    return {"ok": True, "data": entry}


# ---- Get latest data ----
@app.get("/api/latest")
async def get_latest():
    if not sensor_data:
        return {"data": None}
    risk = calculate_risk(sensor_data)
    return {"data": sensor_data[-1], "risk": risk}


@app.get("/api/history")
async def get_history():
    return {"data": sensor_data}


@app.get("/api/risk")
async def get_risk():
    risk = calculate_risk(sensor_data)
    return {"data": risk}


# ---- Citizen Reports API ----
@app.post("/api/report")
async def submit_report(report: CitizenReport):
    entry = {
        "id": str(uuid.uuid4())[:8],
        "report_type": report.report_type,
        "severity": report.severity,
        "lat": report.lat,
        "lng": report.lng,
        "description": report.description,
        "reporter_name": report.reporter_name,
        "photo_data": report.photo_data,
        "timestamp": datetime.now().isoformat(),
        "verified": False,
    }
    citizen_reports.append(entry)
    if len(citizen_reports) > MAX_REPORTS:
        citizen_reports.pop(0)

    # Broadcast to dashboard clients
    message = json.dumps({"type": "report", "data": entry})
    disconnected = []
    for client in connected_clients:
        try:
            await client.send_text(message)
        except:
            disconnected.append(client)
    for client in disconnected:
        connected_clients.remove(client)

    return {"ok": True, "report_id": entry["id"]}


@app.get("/api/reports")
async def get_reports():
    return {"data": citizen_reports}


@app.get("/api/reports/count")
async def get_report_count():
    return {"total": len(citizen_reports), "critical": sum(1 for r in citizen_reports if r["severity"] == "critical"), "high": sum(1 for r in citizen_reports if r["severity"] == "high")}


# ---- Alert Recipients ----
sms_recipients = []
whatsapp_recipients = []

def format_india_phone(phone):
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone.startswith("+"):
        if phone.startswith("0"):
            phone = "+91" + phone[1:]
        elif len(phone) == 10:
            phone = "+91" + phone
        else:
            phone = "+" + phone
    return phone

@app.post("/api/sms/register")
async def register_sms(alert: SMSAlert):
    if alert.phone not in sms_recipients:
        sms_recipients.append(alert.phone)
    return {"ok": True, "message": f"Phone {alert.phone} registered for SMS", "total_recipients": len(sms_recipients)}

@app.post("/api/sms/send")
async def send_sms(alert: SMSAlert):
    phone = format_india_phone(alert.phone)
    if alert.phone not in sms_recipients:
        sms_recipients.append(alert.phone)
    
    # Try Twilio first
    twilio_sid = os.getenv("TWILIO_SID", "")
    twilio_token = os.getenv("TWILIO_TOKEN", "")
    twilio_from = os.getenv("TWILIO_FROM", "")
    if twilio_sid and twilio_token and twilio_from:
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
            data = urllib.parse.urlencode({"To": phone, "From": twilio_from, "Body": alert.message[:160]}).encode()
            auth = base64.b64encode(f"{twilio_sid}:{twilio_token}".encode()).decode()
            req = urllib.request.Request(url, data=data, headers={"Authorization": f"Basic {auth}"})
            urllib.request.urlopen(req, timeout=10)
            return {"ok": True, "sent": True, "via": "Twilio"}
        except Exception as e:
            pass
    
    print(f"[SMS] To: {phone} | {alert.message}")
    return {"ok": True, "sent": False, "via": "demo_mode", "note": "Add TWILIO_SID + TWILIO_TOKEN + TWILIO_FROM env vars on Render for real SMS"}

@app.get("/api/sms/recipients")
async def get_sms_recipients():
    return {"recipients": sms_recipients}

# ---- WhatsApp Alerts API (CallMeBot - free) ----
@app.post("/api/whatsapp/register")
async def register_whatsapp(alert: WhatsAppAlert):
    if alert.phone not in whatsapp_recipients:
        whatsapp_recipients.append(alert.phone)
    return {"ok": True, "message": f"Phone {alert.phone} registered for WhatsApp alerts", "total_recipients": len(whatsapp_recipients), "note": "User must first send 'I allow sendmessage' to +34644704698 on WhatsApp"}

@app.post("/api/whatsapp/send")
async def send_whatsapp(alert: WhatsAppAlert):
    phone = format_india_phone(alert.phone)
    if alert.phone not in whatsapp_recipients:
        whatsapp_recipients.append(alert.phone)
    
    # Try Twilio WhatsApp first
    twilio_sid = os.getenv("TWILIO_SID", "")
    twilio_token = os.getenv("TWILIO_TOKEN", "")
    twilio_from = os.getenv("TWILIO_WHATSAPP_FROM", "")
    if twilio_sid and twilio_token and twilio_from:
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"
            data = urllib.parse.urlencode({"To": f"whatsapp:{phone}", "From": twilio_from, "Body": alert.message[:160]}).encode()
            auth = base64.b64encode(f"{twilio_sid}:{twilio_token}".encode()).decode()
            req = urllib.request.Request(url, data=data, headers={"Authorization": f"Basic {auth}"})
            urllib.request.urlopen(req, timeout=10)
            return {"ok": True, "sent": True, "via": "Twilio WhatsApp"}
        except Exception as e:
            pass
    
    # Try CallMeBot free API
    callmebot_key = os.getenv("CALLMEBOT_API_KEY", "")
    if callmebot_key:
        try:
            encoded_msg = urllib.parse.quote(alert.message[:160])
            url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_msg}&apikey={callmebot_key}"
            urllib.request.urlopen(url, timeout=10)
            return {"ok": True, "sent": True, "via": "CallMeBot WhatsApp"}
        except Exception as e:
            pass
    
    print(f"[WhatsApp] To: {phone} | {alert.message}")
    return {"ok": True, "sent": False, "via": "demo_mode", "note": "Add CALLMEBOT_API_KEY env var on Render. User must send 'I allow sendmessage' to +34644704698 on WhatsApp first."}

@app.get("/api/whatsapp/recipients")
async def get_whatsapp_recipients():
    return {"recipients": whatsapp_recipients}

# ---- Historical Landslide Data ----
@app.get("/api/historical")
async def get_historical():
    hist_path = os.path.join(os.path.dirname(__file__), "historical.json")
    try:
        with open(hist_path, "r") as f:
            data = json.load(f)
        # Calculate summary stats
        total_deaths = sum(d.get("deaths", 0) for d in data)
        total_incidents = len(data)
        years = sorted(set(d["year"] for d in data))
        states = {}
        for d in data:
            loc = d["location"].split(",")[-1].strip()
            states[loc] = states.get(loc, 0) + 1
        return {
            "data": data,
            "summary": {
                "total_incidents": total_incidents,
                "total_deaths": total_deaths,
                "years_covered": f"{min(years)}-{max(years)}",
                "most_affected_states": sorted(states.items(), key=lambda x: -x[1])[:5]
            }
        }
    except FileNotFoundError:
        return {"data": [], "summary": {}}


# ---- Health check ----
@app.get("/health")
async def health():
    return {"status": "ok", "readings": len(sensor_data), "reports": len(citizen_reports), "sms_recipients": len(sms_recipients), "whatsapp_recipients": len(whatsapp_recipients)}


# ---- WebSocket for real-time dashboard updates ----
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)


# ---- Static files ----
@app.get("/sw.js")
async def serve_sw():
    path = os.path.join(os.path.dirname(__file__), "sw.js")
    return FileResponse(path, media_type="application/javascript")

@app.get("/manifest.json")
async def serve_manifest():
    path = os.path.join(os.path.dirname(__file__), "manifest.json")
    return FileResponse(path, media_type="application/json")

@app.get("/historical.json")
async def serve_historical_file():
    path = os.path.join(os.path.dirname(__file__), "historical.json")
    return FileResponse(path, media_type="application/json")


# ---- Serve dashboard ----
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    with open(dashboard_path, "r") as f:
        content = f.read()

    host = os.getenv("RENDER_EXTERNAL_URL", "")
    if host:
        ws_url = host.replace("https://", "wss://").replace("http://", "ws://")
        content = content.replace(
            "`ws://${location.host}/ws`",
            f"'{ws_url}/ws'"
        )

    return HTMLResponse(content=content)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"\n=== Landsafe AI Server v2.0 ===")
    print(f"Dashboard: http://localhost:{port}")
    print(f"API endpoint: POST http://localhost:{port}/api/tilt\n")
    uvicorn.run(app, host="0.0.0.0", port=port)
