"""
Landsafe AI - Backend Server
Receives tilt + moisture data from ESP32, serves the public dashboard.
Includes landslide prediction, weather data, and map.
Deploy to Render for a permanent public URL.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import os
import math

app = FastAPI(title="Landsafe AI", version="2.0.0")

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

# ---- Connected WebSocket clients ----
connected_clients: list[WebSocket] = []

# ---- Data model ----
class TiltReading(BaseModel):
    device_id: str
    tilt: float
    status: str
    ip: str = ""
    moisture: float = 0.0


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


# ---- Health check ----
@app.get("/health")
async def health():
    return {"status": "ok", "readings": len(sensor_data)}


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
