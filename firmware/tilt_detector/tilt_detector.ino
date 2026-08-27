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
const char* WIFI_SSID = "Redmi Note 6 Pro";
const char* WIFI_PASS = "";

// ---- Backend URL ----
const char* SERVER_URL = "https://landsafe-ai.onrender.com/api/tilt";

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

#define SENSITIVITY 0.0039f

// ---- Alert thresholds (wider dead zone) ----
#define TILT_YELLOW  3.0
#define TILT_RED    -3.0
#define DEAD_ZONE    1.5   // Ignore small noise below this

// LED
#define LED_BUILTIN_PIN 2
#define WIFI_LED_PIN 4

// ---- Struct ----
struct AccelData {
  float x;
  float y;
  float z;
};

// ---- Calibration reference (set during calibration) ----
float refX = 0.0;
float refY = 0.0;
float refZ = 0.0;

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

  writeRegister(REG_DATA_FORMAT, 0x08);
  writeRegister(REG_BW_RATE, 0x0A);
  writeRegister(REG_OFSX, 0x00);
  writeRegister(REG_OFSY, 0x00);
  writeRegister(REG_OFSZ, 0x00);
  writeRegister(REG_POWER_CTL, 0x08);

  return true;
}

// ---------- Read accel ----------

AccelData readAccel() {
  uint8_t buffer[6];
  readRegisters(REG_DATAX0, buffer, 6);

  int16_t rawX = (int16_t)((buffer[1] << 8) | buffer[0]);
  int16_t rawY = (int16_t)((buffer[3] << 8) | buffer[2]);
  int16_t rawZ = (int16_t)((buffer[5] << 8) | buffer[4]);

  AccelData data;
  data.x = rawX * SENSITIVITY;
  data.y = rawY * SENSITIVITY;
  data.z = rawZ * SENSITIVITY;
  return data;
}

// ---------- Calibration ----------
// Place sensor FLAT and STILL, then power on.
// This saves the reference readings so flat = 0°.

void calibrateSensor() {
  Serial.println("\n================================");
  Serial.println("  CALIBRATION MODE");
  Serial.println("  Keep sensor FLAT and STILL!");
  Serial.println("  Starting in 3 seconds...");
  Serial.println("================================");
  delay(3000);

  // Throw away first 20 readings (let sensor settle)
  for (int i = 0; i < 20; i++) {
    readAccel();
    delay(10);
  }

  // Take 300 readings and average
  float sumX = 0, sumY = 0, sumZ = 0;
  int samples = 300;

  for (int i = 0; i < samples; i++) {
    AccelData accel = readAccel();
    sumX += accel.x;
    sumY += accel.y;
    sumZ += accel.z;
    delay(5);
  }

  // Save reference = average of what "flat" looks like
  refX = sumX / samples;
  refY = sumY / samples;
  refZ = sumZ / samples;

  Serial.println("\n--- Calibration Result ---");
  Serial.printf("  Reference X: %.4f g\n", refX);
  Serial.printf("  Reference Y: %.4f g\n", refY);
  Serial.printf("  Reference Z: %.4f g\n", refZ);
  Serial.printf("  Flat tilt should be: 0.00°\n");
  Serial.println("  ✅ Calibration DONE!\n");
  Serial.println("  Tilt the sensor now...");
  Serial.println("============================\n");
}

// ---------- Tilt calculation ----------

float calculateTiltAngle(float ax, float ay, float az) {
  // Diff from flat reference
  float dx = ax - refX;
  float dy = ay - refY;
  float dz = az - refZ;

  // Flat when dx≈0, dy≈0
  // Tilt angle = how far from flat (in degrees)
  float tiltRad = atan2(sqrt(dx * dx + dy * dy), abs(dz) + 0.001);
  float tiltDeg = tiltRad * 180.0 / PI;

  // Determine sign based on which axis is tilted
  // Positive = tilting one way, Negative = tilting other way
  if (abs(dx) > abs(dy)) {
    // Tilting along X axis
    if (dx > 0) tiltDeg = -tiltDeg;  // Left tilt = negative
  } else {
    // Tilting along Y axis
    if (dy > 0) tiltDeg = -tiltDeg;  // Forward tilt = negative
  }

  return tiltDeg;
}

// ---------- Moving average ----------

#define FILTER_SIZE 15
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

  String payload = "{";
  payload += "\"device_id\":\"" + String(DEVICE_ID) + "\",";
  payload += "\"tilt\":" + String(tilt, 2) + ",";
  payload += "\"status\":\"" + String(status) + "\",";
  payload += "\"ip\":\"" + WiFi.localIP().toString() + "\"";
  payload += "}";

  int httpCode = http.POST(payload);

  if (httpCode > 0) {
    Serial.printf("POST -> %d\n", httpCode);
  } else {
    Serial.printf("POST failed: %s\n", http.errorToString(httpCode).c_str());
  }

  http.end();
}

// ---------- Determine status (with dead zone) ----------

const char* getTiltStatus(float tilt) {
  // Dead zone: ignore tiny movements
  if (tilt > -DEAD_ZONE && tilt < DEAD_ZONE) return "safe";
  if (tilt > TILT_YELLOW) return "warning";
  if (tilt < TILT_RED) return "danger";
  return "safe";
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

  // CALIBRATE: place sensor flat before this!
  calibrateSensor();

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
    Serial.printf("Tilt: %.2f° [%s] (raw: X=%.3f Y=%.3f Z=%.3f)\n",
                  filteredTilt, status, accel.x, accel.y, accel.z);
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
