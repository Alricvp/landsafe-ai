/*
 * I2C Scanner - finds all devices on the bus
 * Connect HW-123 and run this to check wiring
 */

#include <Wire.h>

#define SDA_PIN 21
#define SCL_PIN 22

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== I2C Scanner ===\n");

  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(100000);

  int found = 0;
  for (byte addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    byte error = Wire.endTransmission();

    if (error == 0) {
      Serial.printf("  Found device at: 0x%02X (%d)\n", addr, addr);
      found++;
    }
  }

  if (found == 0) {
    Serial.println("\n  ❌ No I2C devices found!");
    Serial.println("  Check your wiring:");
    Serial.println("    SDA -> GPIO 21");
    Serial.println("    SCL -> GPIO 22");
    Serial.println("    VCC -> Try 5V instead of 3.3V");
    Serial.println("    GND -> GND");
  } else {
    Serial.printf("\n  ✅ Found %d device(s)\n", found);
  }
}

void loop() {}
