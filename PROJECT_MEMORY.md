# Landsafe AI — Complete Project Memory

## Project Overview
AI-based landslide early warning system for North Eastern India (NER).
Built for MDoNER hackathon.

## Live URLs
- **Dashboard:** https://landsafe-ai.onrender.com
- **GitHub:** https://github.com/Alricvp/landsafe-ai
- **Backend:** FastAPI on Render (auto-deploys from GitHub)

## Hardware (ESP32)
- **Sensor:** MPU-6500 (I2C: SDA→GPIO21, SCL→GPIO22, VCC→3.3V, GND→GND)
- **Moisture:** H9 sensor (A0→GPIO34, VCC→3.3V, GND→GND)
- **WiFi:** "Redmi Note 6 Pro", no password
- **Firmware:** `firmware/tilt_detector/tilt_detector.ino`

## Architecture
```
ESP32 (sensor) → POST /api/tilt → FastAPI (server.py) → WebSocket → dashboard.html
```

## Key Files
| File | Purpose |
|------|---------|
| `backend/server.py` | FastAPI server — API endpoints, WebSocket, risk calculation |
| `backend/dashboard.html` | Single-file dashboard — all HTML/CSS/JS inline (~1170 lines) |
| `backend/sw.js` | Service worker for PWA offline mode |
| `backend/manifest.json` | PWA manifest for installable app |
| `backend/historical.json` | 24 real NER landslide incidents (2015-2025) |
| `firmware/tilt_detector/tilt_detector.ino` | ESP32 Arduino code |

## Dashboard Features (ALL WORKING)
1. **Splash screen** — 2s branded opening
2. **7-tab bottom nav:** Overview → GIS Map → Stations → Alerts → Incident → Report → History
3. **Overview:** Tilt gauge, moisture, density, risk score, siren+vibrate toggles, live log, map
4. **GIS Map:** Leaflet + dark tiles, NE India weather markers (6 cities), corridor polylines, hazard badges
5. **Stations:** 4 station cards with dynamic data (updates every 15 min)
6. **Alerts:** Active alerts + Historical logs with segmented tabs
7. **Incidents:** Incident cards with summaries + diagnostics
8. **Report:** Citizen photo reporting with geo-tag + severity
9. **History:** 24 real incidents, bar charts, timeline
10. **Chatbot:** Green FAB, answers about landslides, moisture, rain, safety, sensors
11. **Notifications:** Browser pop-up on danger/warning (status change only)
12. **Siren:** Loud audio alert (Web Audio API)
13. **Vibration:** Continuous until safe zone
14. **Disconnect detection:** After 10s of no data → gauge resets to 0
15. **5 languages:** English, Hindi, Assamese, Bengali, Manipuri
16. **PWA offline mode:** Service worker + manifest.json

## Thresholds
- Warning: 10° tilt
- Danger: 60° tilt (changed from 40°)
- Moisture warning: 60%, danger: 80%

## Design
- Earthy green/moss theme (Claude's design)
- Fonts: Space Grotesk + Inter + JetBrains Mono + Noto Sans (Indian scripts)
- Map tiles: ArcGIS Dark Gray Base (free, no API key)
- Weather data: Open-Meteo API (free, no API key)

## Backend Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/tilt` | POST | ESP32 sends sensor data |
| `/api/latest` | GET | Latest reading + risk |
| `/api/history` | GET | All readings |
| `/api/risk` | GET | Risk calculation |
| `/api/report` | POST | Citizen report submission |
| `/api/reports` | GET | All citizen reports |
| `/api/historical` | GET | NER landslide history |
| `/ws` | WebSocket | Real-time dashboard updates |
| `/health` | GET | Server health check |
| `/sw.js` | GET | Service worker |
| `/manifest.json` | GET | PWA manifest |

## SMS/WhatsApp (UPCOMING — NOT WORKING)
- Code exists for Twilio SMS and CallMeBot WhatsApp
- Both require API keys/money — marked as "Coming Soon" in dashboard
- Browser notifications + siren + vibration are the working alert methods

## What's NOT Done (MDoNER Requirements)
- ❌ True AI/ML model (only algorithm)
- ❌ Satellite imagery
- ❌ Terrain/slope DEM data
- ❌ Historical records integration (we have static data)
- ❌ Road connectivity status
- ❌ Mobile app (only web)
- ❌ Low-network/offline for remote areas (PWA helps)

## How to Push Changes
1. Edit files locally
2. Open GitHub Desktop
3. Commit changes
4. Push origin
5. Wait 2 min — Render auto-redeploys

## How to Test ESP32 Data
```
curl -X POST https://landsafe-ai.onrender.com/api/tilt -H "Content-Type: application/json" -d "{\"device_id\":\"test\",\"tilt\":65.0,\"moisture\":80.0,\"status\":\"danger\"}"
```

## Rollback
Old builds safe on GitHub. GitHub Desktop → History → right-click commit → Revert.

## Known Issues
- Service worker can cache old versions (bump version in sw.js to fix)
- Bengali translation had extra quote bug (fixed)
- Android notifications needed status-change-only fix (fixed)
