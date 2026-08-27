#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>

const char* WIFI_SSID = "Redmi Note 6 Pro";
const char* WIFI_PASS = "";
const char* SERVER_URL = "https://landsafe-ai.onrender.com/api/tilt";
const char* DEVICE_ID = "sensor-001";

#define ADXL345_ADDR 0x53
#define REG_DEVID     0x00
#define REG_OFSX      0x1E
#define REG_OFSY      0x1F
#define REG_OFSZ      0x20
#define REG_BW_RATE   0x2C
#define REG_POWER_CTL 0x2D
#define REG_DATA_FORMAT 0x31
#define REG_DATAX0    0x32
#define SENSITIVITY   0.0039f

// ---- Thresholds ----
#define TILT_YELLOW  10.0   // Warning at 10 degrees
#define TILT_RED     40.0   // Danger at 40 degrees
#define DEAD_ZONE    2.0

#define LED_BUILTIN_PIN 2
#define WIFI_LED_PIN 4

struct AccelData { float x; float y; float z; };

void writeRegister(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(ADXL345_ADDR); Wire.write(reg); Wire.write(value); Wire.endTransmission();
}
uint8_t readRegister(uint8_t reg) {
  Wire.beginTransmission(ADXL345_ADDR); Wire.write(reg); Wire.endTransmission(false);
  Wire.requestFrom(ADXL345_ADDR, (uint8_t)1); return Wire.read();
}
void readRegisters(uint8_t reg, uint8_t *buffer, uint8_t count) {
  Wire.beginTransmission(ADXL345_ADDR); Wire.write(reg); Wire.endTransmission(false);
  Wire.requestFrom(ADXL345_ADDR, count);
  for (uint8_t i = 0; i < count; i++) buffer[i] = Wire.read();
}

AccelData readAccelOnce() {
  uint8_t buffer[6];
  readRegisters(REG_DATAX0, buffer, 6);
  AccelData data;
  data.x = (int16_t)((buffer[1] << 8) | buffer[0]) * SENSITIVITY;
  data.y = (int16_t)((buffer[3] << 8) | buffer[2]) * SENSITIVITY;
  data.z = (int16_t)((buffer[5] << 8) | buffer[4]) * SENSITIVITY;
  return data;
}

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

bool initADXL345() {
  uint8_t id = readRegister(REG_DEVID);
  if (id != 0xE5) { Serial.printf("ADXL345 not found! ID: 0x%02X\n", id); return false; }
  Serial.println("ADXL345 detected!");
  writeRegister(REG_DATA_FORMAT, 0x08);
  writeRegister(REG_BW_RATE, 0x08);
  writeRegister(REG_OFSX, 0x00);
  writeRegister(REG_OFSY, 0x00);
  writeRegister(REG_OFSZ, 0x00);
  writeRegister(REG_POWER_CTL, 0x08);
  delay(100);
  return true;
}

void calibrateSensor() {
  Serial.println("\n================================");
  Serial.println("  CALIBRATION");
  Serial.println("  Keep sensor FLAT and STILL!");
  Serial.println("  Starting in 3 seconds...");
  Serial.println("================================");
  delay(3000);

  for (int i = 0; i < 20; i++) { readAccelFiltered(); delay(5); }

  float sumX = 0, sumY = 0, sumZ = 0;
  for (int i = 0; i < 200; i++) {
    AccelData a = readAccelFiltered();
    sumX += a.x; sumY += a.y; sumZ += a.z;
    delay(5);
  }

  float avgX = sumX / 200.0;
  float avgY = sumY / 200.0;
  float avgZ = sumZ / 200.0;

  Serial.printf("\n  Before: X=%.4f Y=%.4f Z=%.4f\n", avgX, avgY, avgZ);

  int8_t offX = (int8_t)(-avgX / 0.0156);
  int8_t offY = (int8_t)(-avgY / 0.0156);
  int8_t offZ = (int8_t)(-(avgZ - 1.0) / 0.0156);

  writeRegister(REG_OFSX, offX);
  writeRegister(REG_OFSY, offY);
  writeRegister(REG_OFSZ, offZ);
  delay(100);

  AccelData test = readAccelFiltered();
  Serial.printf("  After:  X=%.4f Y=%.4f Z=%.4f\n", test.x, test.y, test.z);
  Serial.println("  ✅ Calibration DONE!\n");
}

void connectWiFi() {
  Serial.printf("Connecting to WiFi: %s", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500); Serial.print("."); attempts++;
    digitalWrite(WIFI_LED_PIN, !digitalRead(WIFI_LED_PIN));
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.println(WiFi.localIP());
    digitalWrite(WIFI_LED_PIN, HIGH);
  } else {
    Serial.println("\nWiFi failed!");
    digitalWrite(WIFI_LED_PIN, LOW);
  }
}

bool sendInProgress = false;
unsigned long sendStartTime = 0;
float pendingTilt = 0;
const char* pendingStatus = "safe";

void startSend(float tilt, const char* status) {
  if (sendInProgress) return;
  pendingTilt = tilt; pendingStatus = status;
  sendInProgress = true; sendStartTime = millis();
}

void updateSend() {
  if (!sendInProgress) return;
  if (millis() - sendStartTime > 5000) { sendInProgress = false; return; }
  if (WiFi.status() != WL_CONNECTED) { sendInProgress = false; return; }
  HTTPClient http;
  http.setConnectTimeout(3000); http.setTimeout(3000);
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  String payload = "{\"device_id\":\"" + String(DEVICE_ID) + "\",\"tilt\":" + String(pendingTilt, 2) + ",\"status\":\"" + String(pendingStatus) + "\",\"ip\":\"" + WiFi.localIP().toString() + "\"}";
  int httpCode = http.POST(payload);
  if (httpCode > 0) Serial.printf("POST -> %d\n", httpCode);
  http.end();
  sendInProgress = false;
}

const char* getTiltStatus(float tilt) {
  float absTilt = abs(tilt);
  if (absTilt < DEAD_ZONE) return "safe";
  if (absTilt >= TILT_RED) return "danger";      // 40+ degrees = RED
  if (absTilt >= TILT_YELLOW) return "warning";  // 10+ degrees = YELLOW
  return "safe";
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== Landsafe AI - ADXL345 ===\n");
  Serial.println("  Thresholds:");
  Serial.printf("  Safe:    < %d°\n", (int)DEAD_ZONE);
  Serial.printf("  Warning: %d° - %d°\n", (int)TILT_YELLOW, (int)TILT_RED);
  Serial.printf("  Danger:  > %d° (auto siren!)\n\n", (int)TILT_RED);

  pinMode(LED_BUILTIN_PIN, OUTPUT);
  pinMode(WIFI_LED_PIN, OUTPUT);
  digitalWrite(LED_BUILTIN_PIN, LOW);
  digitalWrite(WIFI_LED_PIN, LOW);
  Wire.begin(21, 22);
  Wire.setClock(400000);

  if (!initADXL345()) {
    Serial.println("ADXL345 init failed!");
    while (1) { digitalWrite(LED_BUILTIN_PIN, HIGH); delay(200); digitalWrite(LED_BUILTIN_PIN, LOW); delay(200); }
  }

  calibrateSensor();
  connectWiFi();
  Serial.println("Listening for tilt...\n");
}

void loop() {
  updateSend();
  AccelData accel = readAccelFiltered();

  float tiltRad = atan2(sqrt(accel.x * accel.x + accel.y * accel.y), abs(accel.z));
  float tiltAngle = tiltRad * 180.0 / PI;
  const char* status = getTiltStatus(tiltAngle);

  static unsigned long lastPrint = 0;
  if (millis() - lastPrint >= 500) {
    lastPrint = millis();
    Serial.printf("Tilt: %+.2f° [%s]  X:%.4f Y:%.4f Z:%.4f\n",
                  tiltAngle, status, accel.x, accel.y, accel.z);
  }

  // LED behavior
  if (strcmp(status, "danger") == 0) {
    // Red: fast blink
    digitalWrite(LED_BUILTIN_PIN, HIGH); delay(50);
    digitalWrite(LED_BUILTIN_PIN, LOW); delay(50);
  } else if (strcmp(status, "warning") == 0) {
    // Yellow: slow blink
    digitalWrite(LED_BUILTIN_PIN, HIGH); delay(200);
    digitalWrite(LED_BUILTIN_PIN, LOW); delay(200);
  } else {
    digitalWrite(LED_BUILTIN_PIN, LOW);
  }

  static unsigned long lastSend = 0;
  if (millis() - lastSend >= 2000) { lastSend = millis(); startSend(tiltAngle, status); }

  delay(100);
}
