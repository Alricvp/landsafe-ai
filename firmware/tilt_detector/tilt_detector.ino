/*
 * Landsafe AI - Combined Tilt + Moisture Sensor
 * ESP32 + MPU-6050/6500/9250 (I2C) + Soil Moisture (Analog)
 *
 * Wiring:
 *   MPU VCC  -> ESP32 3.3V
 *   MPU GND  -> ESP32 GND
 *   MPU SDA  -> ESP32 GPIO 21
 *   MPU SCL  -> ESP32 GPIO 22
 *
 *   Moisture VCC -> ESP32 3.3V
 *   Moisture GND -> ESP32 GND
 *   Moisture A0  -> ESP32 GPIO 34
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>

const char* WIFI_SSID = "Redmi Note 6 Pro";
const char* WIFI_PASS = "";
const char* SERVER_URL = "https://landsafe-ai.onrender.com/api/tilt";
const char* DEVICE_ID = "sensor-001";

// ---- MPU Config ----
#define MPU_ADDR      0x68
#define SENSITIVITY_2G 16384.0

// ---- Moisture Config ----
#define MOISTURE_PIN  34
#define MOISTURE_DRY  3200    // ADC value when dry (in air)
#define MOISTURE_WET  1400    // ADC value when submerged

// ---- Thresholds ----
#define TILT_YELLOW   10.0
#define TILT_RED      60.0
#define DEAD_ZONE     2.0
#define MOISTURE_WARN  60.0   // % moisture = warning
#define MOISTURE_DANGER 80.0  // % moisture = danger

#define LED_BUILTIN_PIN 2

struct AccelData { float x; float y; float z; };

float refX = 0, refY = 0, refZ = 0;

// ---- I2C helpers ----
void writeRegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(MPU_ADDR); Wire.write(reg); Wire.write(value); Wire.endTransmission();
}
uint8_t readRegister(uint8_t reg) {
  Wire.beginTransmission(MPU_ADDR); Wire.write(reg); Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, (uint8_t)1); return Wire.read();
}

// ---- Read accel ----
AccelData readAccelOnce() {
  Wire.beginTransmission(MPU_ADDR); Wire.write(0x3B); Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, (uint8_t)6);
  int16_t rawX = (Wire.read() << 8) | Wire.read();
  int16_t rawY = (Wire.read() << 8) | Wire.read();
  int16_t rawZ = (Wire.read() << 8) | Wire.read();
  AccelData data;
  data.x = rawX / SENSITIVITY_2G;
  data.y = rawY / SENSITIVITY_2G;
  data.z = rawZ / SENSITIVITY_2G;
  return data;
}

// ---- Median filter ----
float medianOf9(float *arr) {
  float temp[9];
  for (int i = 0; i < 9; i++) temp[i] = arr[i];
  for (int i = 1; i < 9; i++) {
    float key = temp[i]; int j = i - 1;
    while (j >= 0 && temp[j] > key) { temp[j + 1] = temp[j]; j--; }
    temp[j + 1] = key;
  }
  return temp[4];
}

AccelData readAccelFiltered() {
  float rawX[9], rawY[9], rawZ[9];
  for (int i = 0; i < 9; i++) {
    AccelData a = readAccelOnce();
    rawX[i] = a.x; rawY[i] = a.y; rawZ[i] = a.z;
    delay(2);
  }
  AccelData data;
  data.x = medianOf9(rawX);
  data.y = medianOf9(rawY);
  data.z = medianOf9(rawZ);
  return data;
}

// ---- Read moisture (0-100%) ----
float readMoisture() {
  long sum = 0;
  for (int i = 0; i < 10; i++) {
    sum += analogRead(MOISTURE_PIN);
    delay(5);
  }
  float raw = sum / 10.0;
  
  // Map ADC to percentage (inverted: lower ADC = wetter)
  float pct = map((long)raw, MOISTURE_DRY, MOISTURE_WET, 0, 100);
  if (pct < 0) pct = 0;
  if (pct > 100) pct = 100;
  return pct;
}

// ---- Init MPU ----
bool initMPU() {
  uint8_t id = readRegister(0x75);
  Serial.printf("WHO_AM_I: 0x%02X\n", id);
  if (id != 0x68 && id != 0x70) { Serial.println("MPU not found!"); return false; }
  if (id == 0x70) Serial.println("MPU-6500/9250 detected!");
  else Serial.println("MPU-6050 detected!");
  writeRegister(0x6B, 0x80); delay(100);
  writeRegister(0x6B, 0x00); delay(10);
  writeRegister(0x19, 0x09);
  writeRegister(0x1A, 0x03);
  writeRegister(0x1B, 0x00);
  writeRegister(0x1C, 0x00);
  Serial.println("MPU configured: +/- 2g, 100Hz");
  return true;
}

// ---- Calibration ----
void calibrateSensor() {
  Serial.println("\n================================");
  Serial.println("  CALIBRATION");
  Serial.println("  Keep sensor FLAT and STILL!");
  Serial.println("  Starting in 3 seconds...");
  Serial.println("================================");
  delay(3000);
  for (int i = 0; i < 50; i++) { readAccelOnce(); delay(10); }
  float sumX = 0, sumY = 0, sumZ = 0;
  for (int i = 0; i < 500; i++) {
    AccelData a = readAccelOnce();
    sumX += a.x; sumY += a.y; sumZ += a.z;
    delay(4);
  }
  refX = sumX / 500.0;
  refY = sumY / 500.0;
  refZ = sumZ / 500.0;
  
  // Calibrate moisture
  float dryRead = readMoisture();
  Serial.printf("\n  MPU Flat: X=%.4f Y=%.4f Z=%.4f\n", refX, refY, refZ);
  Serial.printf("  Moisture (air): %.1f%%\n", dryRead);
  Serial.println("  ✅ DONE! Tilt + Moisture ready...\n");
}

// ---- WiFi ----
void connectWiFi() {
  Serial.printf("Connecting to WiFi: %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) { delay(500); Serial.print("."); attempts++; }
  if (WiFi.status() == WL_CONNECTED) Serial.printf("\nConnected! IP: %s\n", WiFi.localIP().toString().c_str());
  else Serial.println("\nWiFi failed!");
}

// ---- Send combined data ----
void sendData(float tilt, float moisture, const char* status) {
  if (WiFi.status() != WL_CONNECTED) { Serial.println("WiFi disconnected!"); return; }
  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(3000);
  
  // Combined payload
  String payload = "{"
    "\"device_id\":\"" + String(DEVICE_ID) + "\","
    "\"tilt\":" + String(tilt, 2) + ","
    "\"moisture\":" + String(moisture, 1) + ","
    "\"status\":\"" + String(status) + "\""
  "}";
  
  Serial.printf("Sending: %s\n", payload.c_str());
  int code = http.POST(payload);
  if (code > 0) Serial.printf("POST -> %d\n", code);
  else Serial.printf("POST failed: %d\n", code);
  http.end();
}

// ---- Setup ----
void setup() {
  Serial.begin(115200); delay(1000);
  Serial.println("\n=== Landsafe AI - Tilt + Moisture ===\n");
  
  pinMode(LED_BUILTIN_PIN, OUTPUT);
  pinMode(MOISTURE_PIN, INPUT);
  
  Wire.begin(21, 22); Wire.setClock(400000);
  
  if (!initMPU()) { Serial.println("Check MPU wiring!"); while (1) { delay(1000); } }
  
  connectWiFi();
  calibrateSensor();
}

// ---- Loop ----
void loop() {
  // Read sensors
  AccelData accel = readAccelFiltered();
  float moisture = readMoisture();
  
  // Calculate tilt
  float dx = accel.x - refX;
  float dy = accel.y - refY;
  float tiltAngle = atan2(sqrt(dx * dx + dy * dy), abs(accel.z)) * 180.0 / PI;
  if (tiltAngle < DEAD_ZONE) tiltAngle = 0;
  
  // Combined status (both tilt AND moisture matter)
  const char* status = "safe";
  
  // Tilt-based
  if (tiltAngle >= TILT_RED) status = "danger";
  else if (tiltAngle >= TILT_YELLOW) status = "warning";
  
  // Moisture-based (if already safe, moisture can upgrade)
  if (strcmp(status, "safe") == 0) {
    if (moisture >= MOISTURE_DANGER) status = "danger";
    else if (moisture >= MOISTURE_WARN) status = "warning";
  }
  // Both dangerous = definitely danger
  else if (strcmp(status, "warning") == 0) {
    if (moisture >= MOISTURE_DANGER || tiltAngle >= TILT_RED) status = "danger";
  }
  
  // Print
  static unsigned long lastPrint = 0;
  if (millis() - lastPrint >= 500) {
    lastPrint = millis();
    Serial.printf("Tilt: %+.2f° | Moisture: %.1f%% | [%s]\n", tiltAngle, moisture, status);
  }
  
  // LED
  if (strcmp(status, "danger") == 0) digitalWrite(LED_BUILTIN_PIN, HIGH);
  else if (strcmp(status, "warning") == 0) { digitalWrite(LED_BUILTIN_PIN, HIGH); delay(200); digitalWrite(LED_BUILTIN_PIN, LOW); delay(200); }
  else digitalWrite(LED_BUILTIN_PIN, LOW);
  
  // Send every 2 seconds
  static unsigned long lastSend = 0;
  if (millis() - lastSend >= 2000) { lastSend = millis(); sendData(tiltAngle, moisture, status); }
  
  delay(100);
}
