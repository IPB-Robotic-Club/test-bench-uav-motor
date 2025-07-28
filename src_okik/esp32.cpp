String inputString = "";    // To store incoming serial data
bool startSending = false;  // Flag to begin sending data

int pwm = 0;
int max_pwm = 100;
int step = 1;

void setup() {
  Serial.begin(115200);
  randomSeed(analogRead(0));
}

void loop() {
  // Check if data is available from Serial
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    inputString += inChar;

    // Check for newline to indicate end of message
    if (inChar == '\n') {
      inputString.trim();  // Remove any \r or spaces
      if (inputString == "START") {
        startSending = true;
        Serial.println(">> ESP32: Start command received");
      }
      inputString = "";  // Clear buffer after processing
    }
  }

  // If start command received, begin sending dummy data
  if (startSending) {
    int gram = pwm * 1.2 + random(0, 6);

    Serial.print("{\"pwm\": ");
    Serial.print(pwm);
    Serial.print(", \"gram\": ");
    Serial.print(gram);
    Serial.println("}");

    pwm += step;

    delay(1000);  // Wait 1 second between each transmission
  }
}
