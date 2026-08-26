"""
Landsafe AI - Backend Server
Receives tilt data from ESP32, serves the public dashboard.
Deploy to Render for a permanent public URL.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import json
import os

app = FastAPI(title="Landsafe AI", version="1.0.0")

# Allow all origins for public access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- In-memory store (last 100 readings) ----
sensor_data = []
MAX_READINGS = 100

# ---- Connected WebSocket clients ----
connected_clients: list[WebSocket] = []

# ---- Data model ----
class TiltReading(BaseModel):
    device_id: str
    tilt: float
    status: str  # "safe", "warning", "danger"
    ip: str = ""


# ---- REST endpoint for ESP32 ----
@app.post("/api/tilt")
async def receive_tilt(reading: TiltReading):
    entry = {
        "device_id": reading.device_id,
        "tilt": reading.tilt,
        "status": reading.status,
        "ip": reading.ip,
        "timestamp": datetime.now().isoformat(),
    }

    sensor_data.append(entry)
    if len(sensor_data) > MAX_READINGS:
        sensor_data.pop(0)

    # Broadcast to all connected dashboard clients
    message = json.dumps(entry)
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
    return {"data": sensor_data[-1]}


@app.get("/api/history")
async def get_history():
    return {"data": sensor_data}


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
    # Read dashboard HTML
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    with open(dashboard_path, "r") as f:
        content = f.read()

    # Fix WebSocket URL for Render (wss:// for HTTPS)
    host = os.getenv("RENDER_EXTERNAL_URL", "")
    if host:
        ws_url = host.replace("https://", "wss://").replace("http://", "ws://")
        content = content.replace(
            "const WS_URL = `ws://${window.location.host}/ws`;",
            f"const WS_URL = '{ws_url}/ws';"
        )
        content = content.replace(
            "const HISTORY_URL = `http://${window.location.host}/api/history`;",
            f"const HISTORY_URL = '{host}/api/history';"
        )

    return HTMLResponse(content=content)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"\n=== Landsafe AI Server ===")
    print(f"Dashboard: http://localhost:{port}")
    print(f"API endpoint: POST http://localhost:{port}/api/tilt\n")
    uvicorn.run(app, host="0.0.0.0", port=port)
