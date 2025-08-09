#include <Arduino.h>
#include <ESP32Servo.h>  // Library untuk kontrol ESC

// Pin Definitions
#define SENSOR_PIN 34
#define MOTOR_PIN 25
#define LED_BUILTIN 2
#define SERIAL_BAUD 115200
#define SAMPLING_MS 1000
#define PWM_MAX 100

// ESC Configuration
#define ESC_MIN_US 1000
#define ESC_MAX_US 2000

// ADC Configuration
#define ADC_SAMPLES 50
#define ADC_MAX 4095
#define THRUST_MAX 1000
#define NOISE_THRESHOLD 100
#define ADC_OFFSET 0

// Global Variables
Servo ESC;
bool isSending = false;
String mode = "DUMMY";
int pwm = 0;

// Calibration Variables
int adc_zero_offset = 0;
bool is_calibrated = false;

// Send status message
void sendStatus(const char* message) {
    Serial.print("STATUS:");
    Serial.println(message);
}

// Calibrate zero-point
void calibrateZeroPoint() {
    sendStatus("CALIBRATING_ZERO");
    long total = 0;
    for (int i = 0; i < 100; i++) {
        total += analogRead(SENSOR_PIN);
        delay(10);
    }
    adc_zero_offset = total / 100;
    is_calibrated = true;
    Serial.print("STATUS:ZERO_CALIBRATED_");
    Serial.println(adc_zero_offset);
}

// Read thrust sensor
int readSensor() {
    long total = 0;
    for (int i = 0; i < ADC_SAMPLES; i++) {
        total += analogRead(SENSOR_PIN);
        delay(5);
    }

    int raw_average = total / ADC_SAMPLES;
    int corrected_value = raw_average - adc_zero_offset;

    // Debug ADC values
    Serial.print("STATUS:ADC_RAW_");
    Serial.print(raw_average);
    Serial.print("_OFFSET_");
    Serial.print(adc_zero_offset);
    Serial.print("_CORRECTED_");
    Serial.println(corrected_value);

    if (!is_calibrated || abs(corrected_value) < NOISE_THRESHOLD || corrected_value < 0) return 0;

    int thrust = map(corrected_value, 0, ADC_MAX - adc_zero_offset, 0, THRUST_MAX);
    return constrain(thrust, 0, THRUST_MAX);
}

// Dummy thrust simulation
int dummyThrust(int pwm) {
    if (pwm == 0 || pwm < 10) return 0;
    float normalized_pwm = (pwm - 10) / 90.0;
    int thrust = (int)(normalized_pwm * normalized_pwm * 500);
    thrust += random(-5, 6);
    return constrain(thrust, 0, 500);
}

// Set motor PWM
void setMotorPWM(int pwmPercent) {
    int us = map(pwmPercent, 0, 100, ESC_MIN_US, ESC_MAX_US);
    ESC.writeMicroseconds(us);
}

// Send data to GUI
void sendData(int pwm, int thrust) {
    Serial.print("{\"pwm\":");
    Serial.print(pwm);
    Serial.print(",\"gram\":");
    Serial.print(thrust);
    Serial.println("}");
}

// Debug ADC
void debugADC() {
    int raw = analogRead(SENSOR_PIN);
    Serial.print("STATUS:RAW_ADC_");
    Serial.println(raw);
}

void setup() {
    pinMode(LED_BUILTIN, OUTPUT);
    pinMode(SENSOR_PIN, INPUT);

    ESP32PWM::allocateTimer(0);
    ESC.setPeriodHertz(50);
    ESC.attach(MOTOR_PIN, ESC_MIN_US, ESC_MAX_US);
    setMotorPWM(0);

    analogReadResolution(12);
    analogSetAttenuation(ADC_11db);

    Serial.begin(SERIAL_BAUD);
    randomSeed(analogRead(0));
    delay(2000);

    mode = "DUMMY";
    sendStatus("ESP_READY_DUMMY_MODE");
    Serial.println("STATUS:Available_Commands_START_STOP_REAL_DUMMY_RESET_CALIBRATE_CALIBRATE_ZERO_CHECK_ADC");
}

void loop() {
    if (Serial.available()) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();

        if (cmd == "START") {
            isSending = true;
            pwm = 0;
            setMotorPWM(0);
            digitalWrite(LED_BUILTIN, HIGH);
            sendStatus("START_OK");
            Serial.print("STATUS:MODE_");
            Serial.println(mode);
        }
        else if (cmd == "STOP") {
            isSending = false;
            pwm = 0;
            setMotorPWM(0);
            digitalWrite(LED_BUILTIN, LOW);
            sendStatus("STOP_OK");
        }
        else if (cmd == "REAL") {
            mode = "REAL";
            sendStatus("MODE_REAL");
            if (!is_calibrated) {
                calibrateZeroPoint();
            }
        }
        else if (cmd == "DUMMY") {
            mode = "DUMMY";
            sendStatus("MODE_DUMMY");
        }
        else if (cmd == "RESET") {
            pwm = 0;
            isSending = false;
            setMotorPWM(0);
            digitalWrite(LED_BUILTIN, LOW);
            sendStatus("RESET_OK");
        }
        else if (cmd == "CALIBRATE" || cmd == "CALIBRATE_ZERO") {
            calibrateZeroPoint();
        }
        else if (cmd == "CHECK_ADC") {
            debugADC();
        }
        else if (cmd == "STATUS") {
            Serial.print("STATUS:MODE_");
            Serial.print(mode);
            Serial.print("_PWM_");
            Serial.print(pwm);
            Serial.print("_RUNNING_");
            Serial.print(isSending ? "YES" : "NO");
            Serial.print("_CALIBRATED_");
            Serial.println(is_calibrated ? "YES" : "NO");
        }
        else if (cmd.startsWith("SET_PWM_")) {
            int manual_pwm = cmd.substring(8).toInt();
            if (manual_pwm >= 0 && manual_pwm <= 100) {
                setMotorPWM(manual_pwm);
                Serial.print("STATUS:MANUAL_PWM_SET_");
                Serial.println(manual_pwm);
            }
        }
        else {
            Serial.print("STATUS:UNKNOWN_COMMAND_");
            Serial.println(cmd);
        }
    }

    if (isSending) {
        setMotorPWM(pwm);
        int thrust = (mode == "DUMMY") ? dummyThrust(pwm) : readSensor();
        sendData(pwm, thrust);

        Serial.print("STATUS:TESTING_PWM_");
        Serial.print(pwm);
        Serial.print("_THRUST_");
        Serial.print(thrust);
        Serial.print("_MODE_");
        Serial.println(mode);

        pwm += 5;
        if (pwm > PWM_MAX) {
            isSending = false;
            pwm = 0;
            setMotorPWM(0);
            digitalWrite(LED_BUILTIN, LOW);
            sendStatus("TEST_COMPLETED");
        }

        delay(SAMPLING_MS);
    }

    static unsigned long lastHeartbeat = 0;
    if (millis() - lastHeartbeat > 5000) {
        if (!isSending) {
            sendStatus("HEARTBEAT");
        }
        lastHeartbeat = millis();
    }
}