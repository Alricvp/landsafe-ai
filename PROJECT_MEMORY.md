# Landsafe AI — Complete Project Memory

## Project Overview
AI-based landslide early warning system for North Eastern India (NER).
Built for MDoNER hackathon (Smart India Hackathon).
**Presentation: September 11, 2025**

## Team
- **Team Name:** scapegoats
- **Email:** crastacalrin@gmail.com
- **Phone:** +91 70229 41015
- **Instagram:** @crastacalrin
- **GitHub:** https://github.com/Alricvp/landsafe-ai

## Live URLs
- **Dashboard:** https://landsafe-ai.onrender.com
- **GitHub:** https://github.com/Alricvp/landsafe-ai
- **Backend:** FastAPI on Render (auto-deploys from GitHub push)

## Hardware (ESP32 + OLED)
- **MCU:** ESP32 DevKit
- **Tilt Sensor:** MPU-6500 (I2C addr 0x68, SDA→GPIO21, SCL→GPIO22, VCC→3.3V, GND→GND)
- **Moisture Sensor:** H9 analog (A0→GPIO34, VCC→3.3V, GND→GND)
- **OLED Display:** 0.96" SSD1306 (I2C addr 0x3C, shares SDA/SCL with MPU)
- **LED:** GPIO 2 (built-in)
- **WiFi:** "Redmi Note 6 Pro", no password
- **Wiring:** OLED + MPU share same I2C bus (different addresses 0x3C vs 0x68)

## Firmware Files
| File | Description |
|------|-------------|
| `firmware/tilt_detector/tilt_detector.ino` | Original — no OLED, median filter + calibration |
| `firmware/tilt_detector_oled/tilt_detector_oled.ino` | **MAIN** — OLED animated intro + median filter + calibration + server posting |

## OLED Firmware Features
1. **Animated boot sequence (~8s):** Landslide animation → Flood animation → Earthquake animation → Logo reveal (radar scan + mountain draw + typewriter text) → System info screen
2. **WiFi connection display** on OLED
3. **500-sample calibration** on startup
4. **9-sample median filter** for smooth readings
5. **3-page cycling display:** Tilt angle → Moisture % → Status summary
6. **Danger flashing** on OLED bottom bar
7. **Server posting** every 2 seconds

## Architecture
```
ESP32 (sensor) → POST /api/tilt → FastAPI (server.py) → WebSocket → dashboard.html
                                                        ↓
                                          Browser notifications + siren + vibration
```

## Key Files
| File | Purpose |
|------|---------|
| `backend/server.py` | FastAPI server — all API endpoints, WebSocket, risk calculation |
| `backend/dashboard.html` | Single-file dashboard — all HTML/CSS/JS inline (~1190 lines) |
| `backend/sw.js` | Service worker for PWA offline mode |
| `backend/manifest.json` | PWA manifest for installable app |
| `backend/historical.json` | 24 real NER landslide incidents (2015-2025) |
| `firmware/tilt_detector_oled/tilt_detector_oled.ino` | **Main ESP32 firmware with OLED** |
| `PROJECT_MEMORY.md` | This file — project context for any AI agent |

## Dashboard Features (ALL WORKING)
1. **Splash screen** — 2s branded opening
2. **7-tab bottom nav:** Overview → GIS Map → Stations → Alerts → Incident → Report → History
3. **Overview:** Tilt gauge, moisture, density, risk score, siren+vibrate toggles, live log, Leaflet map
4. **GIS Map:** Leaflet + dark tiles, NE India weather markers (6 cities), corridor polylines, hazard badges
5. **Stations:** 4 station cards (Gangtok, Haflong, Cherrapunji, Tupul) with dynamic data
6. **Alerts:** Active alerts (3) + Historical logs (3) with segmented tabs
7. **Incidents:** Incident cards with summaries + diagnostics
8. **Report:** Citizen photo reporting with geo-tag + severity + location
9. **History:** 24 real incidents, charts, timeline
10. **Chatbot:** Green FAB, answers about landslides, moisture, rain, safety, sensors
11. **Notifications:** Browser pop-up on danger/warning (status change only)
12. **Siren:** Loud audio alert (Web Audio API, max volume)
13. **Vibration:** Continuous until safe zone
14. **Disconnect detection:** After 10s of no data → gauge resets to 0
15. **5 languages:** English, Hindi, Assamese, Bengali, Manipuri
16. **PWA offline mode:** Service worker + manifest.json
17. **Contact footer:** Email, phone, Instagram links + "Built by Scapegoats"
18. **SMS/WhatsApp "Coming Soon":** Professional wording, no funding mention

## Thresholds
- Warning: 10° tilt
- Danger: 60° tilt (changed from original 40°)
- Moisture warning: 60%, danger: 80%
- Dead zone: 2° (ignore tiny movements)

## Design
- Earthy green/moss theme
- Fonts: Space Grotesk + Inter + JetBrains Mono + Noto Sans (Indian scripts)
- Map tiles: ArcGIS Dark Gray Base (free, no API key)
- Weather data: Open-Meteo API (free, no API key)
- Color palette: bg #10130F, surface #171B16, moss #6FA97D, ochre #D69A4E, rust #C25B45

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
- Dashboard shows "Coming Soon" with professional wording
- Twilio account was suspended (rejected reactivation)
- CallMeBot WhatsApp API unreliable
- Currently using browser notifications + siren + vibration for alerts
- **Presentation note:** Frame as "planned feature" not "broken feature"

## MDoNER Requirements Checklist
- ✅ Real-time GIS dashboard and risk heatmaps
- ⚠️ AI/ML-based predictive analytics (algorithm-based, not true ML)
- ✅ Mobile/web application for field reporting and alerts (PWA)
- ⚠️ Integration with IMD weather APIs (using Open-Meteo, IMD planned)
- 🔜 Automated SMS/app-based early warning system (browser notifications work, SMS planned)
- ✅ Cloud-based architecture with offline sync support (PWA + service worker)
- ❌ Satellite imagery integration
- ❌ Terrain/slope DEM data
- ❌ Road connectivity status tracking
- ✅ Risk severity levels
- ✅ Weather-linked risk forecasts
- ✅ Emergency response prioritization (incident tab)
- ✅ Multilingual notifications (5 languages)
- ✅ Low-network/offline functionality (PWA)

## Presentation Notes (Sept 11)
- PPT being made on Canva by teammate
- Focus on SOFTWARE PLATFORM, not cheap hardware
- ESP32 is proof-of-concept demo, not the product
- Product is the monitoring PLATFORM (cloud + dashboard + AI + alerts)
- Frame as government-grade system, not hobby project
- Professional contact info in footer (email, phone, Instagram)
- Delete SIH instruction slide before uploading PDF

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
Last stable build: commit 63c9364 (Aug 31)

## Known Issues
- Service worker can cache old versions (bump version in sw.js to fix)
- Bengali translation had extra quote bug (fixed)
- Android notifications needed status-change-only fix (fixed)
- OLED previously didn't work (old hardware issue — new OLED works fine)

## Instructions for Next AI Agent
1. Read this file first
2. Key files: `backend/server.py` and `backend/dashboard.html`
3. Dashboard is ONE file with all HTML/CSS/JS inline — be careful editing
4. Always check `python -m py_compile server.py` after backend changes
5. The user is a college student — keep explanations simple
6. Project repo: https://github.com/Alricvp/landsafe-ai
7. Deployment: push to GitHub → Render auto-deploys in ~2 min
