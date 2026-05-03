// =========================
// Created by Alicia (2025)
// =========================

#include <Arduino.h>
#include "HX711.h"

// HX711 pins (same as your setup)
#define HX711_DT 4
#define HX711_SCK 5

HX711 scale;

// 👉 use your previous calibration factor
float calibration_factor = -201;  

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("HX711 Test Starting...");

  scale.begin(HX711_DT, HX711_SCK);

  if (scale.is_ready()) {
    Serial.println("HX711 is READY");
  } else {
    Serial.println("HX711 NOT FOUND");
  }

  // Set calibration
  scale.set_scale(calibration_factor);

  // Tare (zero)
  Serial.println("Taring... Remove all weight");
  delay(3000);
  scale.tare();

  Serial.println("Ready to measure");
}

void loop() {
  if (scale.is_ready()) {

    long raw = scale.read();  // raw ADC value
    float weight = scale.get_units(10);  // average 10 samples

    Serial.print("RAW: ");
    Serial.print(raw);

    Serial.print(" | Weight: ");
    Serial.print(weight);
    Serial.println(" g");

  } else {
    Serial.println("HX711 not ready");
  }

  delay(500);
}
