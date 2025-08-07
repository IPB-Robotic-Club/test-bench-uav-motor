#include <Arduino.h>

bool isSending = false;
String mode = "REAL";  // default
int pwm = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);
}

void loop() {
  // Cek perintah dari GUI
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "START") {
      isSending = true;
    } else if (cmd == "DUMMY") {
      mode = "DUMMY";
    } else if (cmd == "REAL") {
      mode = "REAL";
    }
  }

  // Kirim data jika mode aktif
  if (isSending) {
    int thrust;
    if (mode == "DUMMY") {
      thrust = dummyThrust(pwm);  // mode simulasi
    } else {
      thrust = readSensor();      // mode real sensor
    }

    Serial.print("{\"pwm\": ");
    Serial.print(pwm);
    Serial.print(", \"gram\": ");
    Serial.print(thrust);
    Serial.println("}");

    pwm += 5;
    if (pwm > 100) {
      pwm = 0;
      isSending = false;
    }

    delay(200);  // sampling rate
  }
}

// Dummy linear
int dummyThrust(int pwm) {
  return pwm * 2;  // misal 0–200 gram
}

// Simulasi pembacaan sensor asli
int readSensor() {
  // misalnya dari analogRead(), dikonversi ke gram
  int analog = analogRead(34);
  return map(analog, 0, 4095, 0, 300);
}