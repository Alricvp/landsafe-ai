/*
 * Landsafe AI — Tilt Detector with OLED Display
 * Hardware: ESP32 + MPU-6500 + H9 Moisture Sensor + 0.96" SSD1306 OLED
 * 
 * Wiring:
 *   MPU-6500:  SDA→GPIO21, SCL→GPIO22, VCC→3.3V, GND→GND
 *   Moisture:  A0→GPIO34, VCC→3.3V, GND→GND
 *   OLED:      SDA→GPIO21, SCL→GPIO22, VCC→3.3V, GND→GND (I2C addr 0x3C)
 * 
 * Libraries needed (install in Arduino IDE):
 *   - Adafruit SSD1306
 *   - Adafruit GFX Library
 *   - Wire (built-in)
 */

#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ===== CONFIGURATION =====
const char* WIFI_SSID = "Redmi Note 6 Pro";
const char* WIFI_PASS = "";
const char* SERVER_URL = "https://landsafe-ai.onrender.com/api/tilt";
const char* DEVICE_ID = "esp32-ner-001";

// ===== OLED SETUP =====
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define OLED_ADDR 0x3C
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// ===== MPU-6500 I2C =====
#define MPU_ADDR 0x68

// ===== PINS =====
#define MOISTURE_PIN 34

// ===== THRESHOLDS =====
#define WARN_THRESHOLD 10.0
#define DANGER_THRESHOLD 60.0
#define MOISTURE_WARN 60
#define MOISTURE_DANGER 80

// ===== STATE =====
float tilt = 0.0;
float rawAx = 0, rawAy = 0, rawAz = 0;
int moistureRaw = 0;
float moisturePercent = 0.0;
String status = "safe";
String wifiStatus = "Connecting...";
unsigned long lastSend = 0;
unsigned long lastDisplayUpdate = 0;
int displayPage = 0;  // 0=tilt, 1=moisture, 2=status
bool introDone = false;
unsigned long introStart = 0;

// ===== TEAM LOGO BITMAP (32x32) =====
static const unsigned char PROGMEM logo_bmp[] = {
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x03, 0xC0, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x0F, 0xF0, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x3F, 0xFC, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x7F, 0xFE, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x01, 0xFF, 0xFF, 0x80, 0x00, 0x00, 0x00,
  0x00, 0x03, 0xFF, 0xFF, 0xC0, 0x00, 0x00, 0x00,
  0x00, 0x07, 0xF0, 0x0F, 0xE0, 0x00, 0x00, 0x00,
  0x00, 0x0F, 0xC0, 0x03, 0xF0, 0x00, 0x00, 0x00,
  0x00, 0x1F, 0x00, 0x00, 0xF8, 0x00, 0x00, 0x00,
  0x00, 0x3E, 0x00, 0x00, 0x7C, 0x00, 0x00, 0x00,
  0x00, 0x7C, 0x00, 0x00, 0x3E, 0x00, 0x00, 0x00,
  0x00, 0xF8, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00,
  0x01, 0xF0, 0x00, 0x00, 0x0F, 0x80, 0x00, 0x00,
  0x03, 0xE0, 0x00, 0x00, 0x07, 0xC0, 0x00, 0x00,
  0x07, 0xC0, 0x00, 0x00, 0x03, 0xE0, 0x00, 0x00,
  0x0F, 0x80, 0x00, 0x00, 0x01, 0xF0, 0x00, 0x00,
  0x1F, 0x00, 0x00, 0x00, 0x00, 0xF8, 0x00, 0x00,
  0x3E, 0x00, 0x00, 0x00, 0x00, 0x7C, 0x00, 0x00,
  0x7C, 0x00, 0x00, 0x00, 0x00, 0x3E, 0x00, 0x00,
  0xF8, 0x00, 0x00, 0x00, 0x00, 0x1F, 0x00, 0x00,
  0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00,
  0x7F, 0xFF, 0xFF, 0xFF, 0xFF, 0xFE, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};

// ===== SETUP =====
void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);  // SDA, SCL
  
  // Initialize OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println("OLED init failed!");
    while (true);
  }
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  
  // Show intro screen
  showIntro();
  
  // Initialize MPU-6500
  initMPU();
  
  // Connect WiFi
  connectWiFi();
  
  introDone = true;
  Serial.println("Landsafe AI ready!");
}

// ===== INTRO SCREEN =====
void showIntro() {
  introStart = millis();
  
  // Frame 1: Logo (0-2s)
  display.clearDisplay();
  display.drawBitmap(48, 0, logo_bmp, 32, 32, SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(20, 38);
  display.println(F("LANDSAFE AI"));
  display.setCursor(25, 50);
  display.setTextSize(1);
  display.println(F("by scapegoats"));
  display.display();
  delay(2500);
  
  // Frame 2: System info (2-3.5s)
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(10, 5);
  display.println(F("Landslide Monitoring"));
  display.setCursor(10, 18);
  display.println(F("System for NER"));
  
  // Draw separator line
  display.drawLine(10, 30, 118, 30, SSD1306_WHITE);
  
  display.setCursor(10, 38);
  display.println(F("MPU-6500 + H9 Sensor"));
  display.setCursor(10, 50);
  display.println(F("Initializing..."));
  display.display();
  delay(1500);
}

// ===== MPU-6500 INIT =====
void initMPU() {
  // Wake up MPU-6500
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B);  // PWR_MGMT_1
  Wire.write(0x00);  // Clear sleep bit
  Wire.endTransmission(true);
  
  // Set accel range to +/- 4g
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1C);  // ACCEL_CONFIG
  Wire.write(0x08);  // +/- 4g
  Wire.endTransmission(true);
  
  // Set DLPF for smoother readings
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x1A);  // CONFIG
  Wire.write(0x03);  // 44Hz bandwidth
  Wire.endTransmission(true);
  
  Serial.println("MPU-6500 initialized");
}

// ===== READ ACCEL DATA =====
void readAccel() {
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);  // ACCEL_XOUT_H
  Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)MPU_ADDR, (uint8_t)6, (uint8_t)true);
  
  rawAx = (Wire.read() << 8 | Wire.read()) / 8192.0;  // +/- 4g
  rawAy = (Wire.read() << 8 | Wire.read()) / 8192.0;
  rawAz = (Wire.read() << 8 | Wire.read()) / 8192.0;
}

// ===== READ MOISTURE =====
void readMoisture() {
  moistureRaw = analogRead(MOISTURE_PIN);
  // Map raw ADC (0-4095) to percentage (dry=high, wet=low)
  moisturePercent = map(moistureRaw, 4095, 0, 0, 100);
  moisturePercent = constrain(moisturePercent, 0, 100);
}

// ===== CALCULATE TILT =====
float calculateTilt() {
  // Tilt angle from accelerometer (degrees)
  float tiltX = atan2(rawAy, sqrt(rawAx * rawAx + rawAz * rawAz)) * 180.0 / PI;
  return abs(tiltX);
}

// ===== DETERMINE STATUS =====
String determineStatus() {
  if (tilt >= DANGER_THRESHOLD || moisturePercent >= MOISTURE_DANGER) {
    return "danger";
  } else if (tilt >= WARN_THRESHOLD || moisturePercent >= MOISTURE_WARN) {
    return "warning";
  }
  return "safe";
}

// ===== CONNECT WIFI =====
void connectWiFi() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(10, 5);
  display.println(F("Connecting to WiFi..."));
  display.setCursor(10, 18);
  display.println(WIFI_SSID);
  display.display();
  
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
    
    // Animated dots on OLED
    display.setCursor(10 + (attempts * 4), 35);
    display.print(F("."));
    display.display();
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    wifiStatus = "Connected";
    Serial.println("\nWiFi connected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  } else {
    wifiStatus = "Failed";
    Serial.println("\nWiFi failed!");
  }
  
  // Show connection result
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(10, 20);
  if (WiFi.status() == WL_CONNECTED) {
    display.println(F("WiFi Connected!"));
    display.setCursor(10, 35);
    display.println(WiFi.localIP());
  } else {
    display.println(F("WiFi Failed!"));
    display.setCursor(10, 35);
    display.println(F("Check credentials"));
  }
  display.display();
  delay(1500);
}

// ===== DISPLAY PAGES =====
void updateDisplay() {
  if (!introDone) return;
  
  unsigned long now = millis();
  if (now - lastDisplayUpdate < 500) return;  // Update every 500ms
  lastDisplayUpdate = now;
  
  display.clearDisplay();
  
  // Header
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print(F("LANDSAFE AI"));
  
  // WiFi status indicator
  display.setCursor(90, 0);
  if (WiFi.status() == WL_CONNECTED) {
    display.print(F("[OK]"));
  } else {
    display.print(F("[--]"));
  }
  
  // Separator line
  display.drawLine(0, 10, 127, 10, SSD1306_WHITE);
  
  // Page content
  switch (displayPage) {
    case 0:  // Tilt page
      drawTiltPage();
      break;
    case 1:  // Moisture page
      display.setCursor(0, 55);
      display.print(F("T:"));
      display.print(tilt, 1);
      display.print(F(" M:"));
      display.print((int)moisturePercent);
      display.print(F("%"));
      drawMoisturePage();
      break;
    case 2:  // Status page
      drawStatusPage();
      break;
  }
  
  // Bottom bar with status
  display.drawLine(0, 53, 127, 53, SSD1306_WHITE);
  display.setCursor(0, 55);
  
  if (status == "danger") {
    // Flashing danger
    if ((millis() / 500) % 2 == 0) {
      display.print(F("! DANGER !"));
    } else {
      display.print(F("           "));
    }
  } else if (status == "warning") {
    display.print(F("* WARNING *"));
  } else {
    display.print(F("  STATUS OK"));
  }
  
  display.display();
  
  // Cycle pages every 3 seconds
  if (now - (lastDisplayUpdate - 500) > 3000) {
    displayPage = (displayPage + 1) % 3;
  }
}

void drawTiltPage() {
  // Big tilt number
  display.setTextSize(2);
  display.setCursor(10, 15);
  display.print(tilt, 1);
  display.setTextSize(1);
  display.setCursor(90, 20);
  display.print(F("deg"));
  
  // Tilt bar
  int barWidth = map(min(tilt, 90.0), 0, 90, 0, 110);
  display.drawRect(10, 38, 112, 8, SSD1306_WHITE);
  display.fillRect(10, 38, barWidth, 8, SSD1306_WHITE);
  
  // Labels
  display.setCursor(10, 43);
  display.print(F("0"));
  display.setCursor(55, 43);
  display.print(F("45"));
  display.setCursor(105, 43);
  display.print(F("90"));
}

void drawMoisturePage() {
  // Moisture value
  display.setTextSize(2);
  display.setCursor(10, 15);
  display.print((int)moisturePercent);
  display.setTextSize(1);
  display.setCursor(55, 20);
  display.print(F("%%"));
  
  // Moisture bar
  int barWidth = map((int)moisturePercent, 0, 100, 0, 110);
  display.drawRect(10, 38, 112, 8, SSD1306_WHITE);
  display.fillRect(10, 38, barWidth, 8, SSD1306_WHITE);
  
  // Labels
  display.setCursor(10, 43);
  display.print(F("Dry"));
  display.setCursor(50, 43);
  display.print(F("50%%"));
  display.setCursor(100, 43);
  display.print(F("Wet"));
}

void drawStatusPage() {
  display.setTextSize(1);
  display.setCursor(0, 15);
  display.print(F("Tilt:   "));
  display.print(tilt, 1);
  display.print(F(" deg"));
  
  display.setCursor(0, 28);
  display.print(F("Moist:  "));
  display.print((int)moisturePercent);
  display.print(F(" %%"));
  
  display.setCursor(0, 41);
  display.print(F("Status: "));
  if (status == "danger") {
    display.print(F("DANGER!"));
  } else if (status == "warning") {
    display.print(F("WARNING"));
  } else {
    display.print(F("SAFE"));
  }
}

// ===== SEND TO SERVER =====
void sendToServer() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected, skipping send");
    return;
  }
  
  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  
  String json = "{";
  json += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  json += "\"tilt\":" + String(tilt, 2) + ",";
  json += "\"moisture\":" + String(moisturePercent, 1) + ",";
  json += "\"status\":\"" + status + "\"";
  json += "}";
  
  int httpResponseCode = http.POST(json);
  
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.print("POST -> ");
    Serial.println(httpResponseCode);
    
    // Show brief send confirmation on OLED
    display.setCursor(100, 0);
    display.print(F("TX"));
    display.display();
  } else {
    Serial.print("POST failed: ");
    Serial.println(httpResponseCode);
  }
  
  http.end();
}

// ===== MAIN LOOP =====
void loop() {
  // Read sensors
  readAccel();
  readMoisture();
  
  // Calculate values
  tilt = calculateTilt();
  status = determineStatus();
  
  // Print to serial
  Serial.print("Tilt: ");
  Serial.print(tilt, 2);
  Serial.print("° [");
  Serial.print(status);
  Serial.print("]  M:");
  Serial.print(moisturePercent, 1);
  Serial.print("% dx:");
  Serial.print(rawAx, 4);
  Serial.print(" dy:");
  Serial.print(rawAy, 4);
  Serial.print(" dz:");
  Serial.println(rawAz, 4);
  
  // Update OLED display
  updateDisplay();
  
  // Send to server every 2 seconds
  unsigned long now = millis();
  if (now - lastSend >= 2000) {
    lastSend = now;
    sendToServer();
  }
  
  delay(50);  // 50ms loop
}
