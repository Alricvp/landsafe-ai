/*
 * Landsafe AI - Tilt Detector with WiFi + Backend
 * ESP32 + ADXL345 (I2C)
 * 
 * Wiring:
 *   ADXL345 VCC  -> ESP32 3.3V
 *   ADXL345 GND  -> ESP32 GND
 *   ADXL345 CS   -> ESP32 3.3V
 *   ADXL345 SDA  -> ESP32 GPIO 21
 *   ADXL345 SCL  -> ESP32 GPIO 22
 *   ADXL345 SDO  -> ESP32 GND (address 0x53)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>

// ---- WiFi Config ----
const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";

// ---- Backend URL ----
// Change to your server's public IP or domain
const char* SERVER_URL = "http://YOUR_SERVER_IP:8000/api/tilt";
// Example: "http://192.168.1.100:8000/api/tilt"
// For public: "http://yourdomain.com:8000/api/tilt"

// ---- Device ID ----
const char* DEVICE_ID = "sensor-001";

// ADXL345 I2C address
#define ADXL345_ADDR 0x53

// ADXL345 registers
#define REG_DEVID          0x00
#define REG_OFSX           0x1E
#define REG_OFSY           0x1F
#define REG_OFSZ           0x20
#define REG_BW_RATE        0x2C
#define REG_POWER_CTL      0x2D
#define REG_DATA_FORMAT    0x31
#define REG_DATAX0         0x32

#define SENSITIVITY 0.0039f  // +/- 2g -> 3.9 mg/LSB

// ---- Alert thresholds ----
#define TILT_YELLOW  2.0    // Warning when tilt > 2°
#define TILT_RED    -2.0    // Danger when tilt < -2°

// LED
#define LED_BUILTIN_PIN 2

// ---- WiFi Status LED ----
#define WIFI_LED_PIN 4

// ---------- I2C helpers ----------

void writeRegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(ADXL345_ADDR);
  Wire.write(reg);
  Wire.write(value);
  Wire.endTransmission();
}

uint8_t readRegister(uint8_t reg) {
  Wire.beginTransmission(ADXL345_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(ADXL345_ADDR, (uint8_t)1);
  return Wire.read();
}

void readRegisters(uint8_t reg, uint8_t *buffer, uint8_t count) {
  Wire.beginTransmission(ADXL345_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(ADXL345_ADDR, count);
  for (uint8_t i = 0; i < count; i++) {
    buffer[i] = Wire.read();
  }
}

// ---------- ADXL345 setup ----------

bool initADXL345() {
  uint8_t deviceId = readRegister(REG_DEVID);
  if (deviceId != 0xE5) {
    Serial.printf("ADXL345 not found! Got ID: 0x%02X\n", deviceId);
    return false;
  }
  Serial.println("ADXL345 detected");

  writeRegister(REG_DATA_FORMAT, 0x08);  // Full res, +/- 2g
  writeRegister(REG_BW_RATE, 0x0A);      // 100Hz
  writeRegister(REG_OFSX, 0x00);
  writeRegister(REG_OFSY, 0x00);
  writeRegister(REG_OFSZ, 0x00);
  writeRegister(REG_POWER_CTL, 0x08);    // Measure mode

  return true;
}

// ---------- Read accel ----------

struct AccelData { float x, y, z; };

AccelData readAccel() {
  uint8_t buffer[6];
  readRegisters(REG_DATAX0, buffer, 6);

  int16_t rawX = (int16_t)((buffer[1] << 8) | buffer[0]);
  int16_t rawY = (int16_t)((buffer[3] << 8) | buffer[2]);
  int16_t rawZ = (int16_t)((buffer[5] << 8) | buffer[4]);

  return { rawX * SENSITIVITY, rawY * SENSITIVITY, rawZ * SENSITIVITY };
}

float calculateTiltAngle(float ax, float ay, float az) {
  return atan2(az, sqrt(ax * ax + ay * ay)) * 180.0 / PI;
}

// ---------- Moving average ----------

#define FILTER_SIZE 10
float filterBuffer[FILTER_SIZE];
uint8_t filterIndex = 0;

float movingAverage(float newVal) {
  filterBuffer[filterIndex] = newVal;
  filterIndex = (filterIndex + 1) % FILTER_SIZE;

  float sum = 0;
  for (uint8_t i = 0; i < FILTER_SIZE; i++) sum += filterBuffer[i];
  return sum / FILTER_SIZE;
}

// ---------- WiFi ----------

void connectWiFi() {
  Serial.printf("Connecting to WiFi: %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
    digitalWrite(WIFI_LED_PIN, !digitalRead(WIFI_LED_PIN));
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    digitalWrite(WIFI_LED_PIN, HIGH);
  } else {
    Serial.println("\nWiFi failed! Running offline.");
    digitalWrite(WIFI_LED_PIN, LOW);
  }
}

// ---------- Send data to backend ----------

void sendDataToServer(float tilt, const char* status) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected, retrying...");
    connectWiFi();
    return;
  }

  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");

  // Build JSON payload
  String payload = "{";
  payload += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  payload += "\"tilt\":" + String(tilt, 2) + ",";
  payload += "\"status\":\"" + String(status) + "\",";
  payload += "\"ip\":\"" + WiFi.localIP().toString() + "\"";
  payload += "}";

  int httpCode = http.POST(payload);

  if (httpCode > 0) {
    Serial.printf("POST %s -> %d\n", SERVER_URL, httpCode);
  } else {
    Serial.printf("POST failed: %s\n", http.errorToString(httpCode).c_str());
  }

  http.end();
}

// ---------- Determine status ----------

const char* getTiltStatus(float tilt) {
  if (tilt > TILT_YELLOW) return "warning";   // Yellow
  if (tilt < TILT_RED) return "danger";       // Red
  return "safe";                               // Green
}

// ---------- Main ----------

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n=== Landsafe AI - Tilt Detector ===\n");

  pinMode(LED_BUILTIN_PIN, OUTPUT);
  pinMode(WIFI_LED_PIN, OUTPUT);
  digitalWrite(LED_BUILTIN_PIN, LOW);
  digitalWrite(WIFI_LED_PIN, LOW);

  Wire.begin(21, 22);
  Wire.setClock(400000);

  if (!initADXL345()) {
    Serial.println("ADXL345 init failed! Halting.");
    while (1) {
      digitalWrite(LED_BUILTIN_PIN, HIGH);
      delay(200);
      digitalWrite(LED_BUILTIN_PIN, LOW);
      delay(200);
    }
  }

  for (uint8_t i = 0; i < FILTER_SIZE; i++) filterBuffer[i] = 0.0;

  connectWiFi();
  Serial.println("\nListening for tilt...\n");
}

void loop() {
  AccelData accel = readAccel();
  float tiltAngle = calculateTiltAngle(accel.x, accel.y, accel.z);
  float filteredTilt = movingAverage(tiltAngle);
  const char* status = getTiltStatus(filteredTilt);

  // Serial output
  static unsigned long lastPrint = 0;
  if (millis() - lastPrint >= 500) {
    lastPrint = millis();
    Serial.printf("Tilt: %.2f° [%s]\n", filteredTilt, status);
  }

  // LED alert
  if (strcmp(status, "danger") == 0) {
    digitalWrite(LED_BUILTIN_PIN, HIGH);
  } else if (strcmp(status, "warning") == 0) {
    digitalWrite(LED_BUILTIN_PIN, HIGH);
    delay(100);
    digitalWrite(LED_BUILTIN_PIN, LOW);
    delay(100);
  } else {
    digitalWrite(LED_BUILTIN_PIN, LOW);
  }

  // Send to backend every 2 seconds
  static unsigned long lastSend = 0;
  if (millis() - lastSend >= 2000) {
    lastSend = millis();
    sendDataToServer(filteredTilt, status);
  }

  delay(100);
}
