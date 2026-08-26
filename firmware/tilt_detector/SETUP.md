# ESP32 Setup Guide

## Before Uploading

Edit these lines in `tilt_detector.ino`:

```cpp
const char* WIFI_SSID = "YOUR_WIFI_NAME";      // Your WiFi name
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";   // Your WiFi password
const char* SERVER_URL = "https://your-app.onrender.com/api/tilt";  // Your Render URL
```

## How to Find Your Render URL

After deploying to Render (see main guide):
1. Go to your Render dashboard
2. Click on your service
3. Copy the URL (looks like `https://landsafe-ai.onrender.com`)
4. Paste it in the firmware

## Wiring

```
ADXL345      ESP32
───────      ─────
VCC     →    3.3V
GND     →    GND
CS      →    3.3V
SDA     →    GPIO 21
SCL     →    GPIO 22
SDO     →    GND
```

## Upload Steps

1. Connect ESP32 via USB
2. Open `tilt_detector.ino` in Arduino IDE
3. Edit WiFi + Server URL
4. Select board: **Tools → Board → ESP32 Dev Module**
5. Select port: **Tools → Port → COMx (ESP32)**
6. Click Upload
7. Open Serial Monitor (115200 baud) to see data
