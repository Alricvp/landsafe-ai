/*
 * node2_esp32_speaker.ino
 * Node 2 — Bluetooth alarm speaker (A2DP sink) for MAX98357A.
 *
 * IMPORTANT — BOARD CHOICE:
 *   Bluetooth Classic / A2DP exists ONLY on the ORIGINAL ESP32.
 *   ESP32-S3 / S2 / C3 are BLE-only — this sketch will NOT run there.
 *   Flash this on an "ESP32 Dev Module" (classic ESP32).
 *   (Run the telemetry node on whichever board you have left; node1
 *    is chip-agnostic and works on ESP32 and ESP32-S3 unchanged.)
 *
 * Libraries (Arduino Library Manager):
 *   - AudioTools          by Phil Schatzmann
 *   - BluetoothA2DPSink   (ESP32-A2DP, Phil Schatzmann)
 *
 * Wiring — MAX98357A to classic ESP32:
 *   MAX98357A VIN  -> 3.3V (or 5V per board silkscreen)
 *   MAX98357A GND  -> GND
 *   MAX98357A BCLK -> GPIO 26
 *   MAX98357A LRC  -> GPIO 25
 *   MAX98357A DIN  -> GPIO 22
 *   MAX98357A SD   -> leave per module default (default gain/mono mix)
 *   MAX98357A SPK+/- -> 4..8 ohm speaker ONLY — never a GPIO
 *
 * Use: power the board, pair the phone with "ESP32-Speaker",
 * play audio — it comes out of the speaker.
 */

#include "AudioTools.h"
#include "BluetoothA2DPSink.h"

I2SStream i2s;
BluetoothA2DPSink a2dp_sink(i2s);

// ===== EDIT ONLY THIS BLOCK =====
const int PIN_BCLK  = 26;
const int PIN_LRC   = 25;
const int PIN_DIN   = 22;
const char* BT_NAME = "ESP32-Speaker";
// ================================

void setup() {
  Serial.begin(115200);

  auto cfg = i2s.defaultConfig(TX_MODE);
  cfg.pin_bck  = PIN_BCLK;
  cfg.pin_ws   = PIN_LRC;
  cfg.pin_data = PIN_DIN;
  i2s.begin(cfg);

  a2dp_sink.start(BT_NAME);
  Serial.printf("\n%s: pairing as \"%s\" (BCLK=%d LRC=%d DIN=%d)\n",
                "Node 2 speaker", BT_NAME, PIN_BCLK, PIN_LRC, PIN_DIN);
}

void loop() {}
