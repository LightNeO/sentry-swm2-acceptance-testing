#include <Arduino.h>

// Each output drives an optocoupler LED (or an open-collector transistor).
// Never connect these 5 V outputs directly to the ESP32 GPIO pins.
// A2-A5 are used as digital pins. The interface is open-drain in software:
// pressed = OUTPUT/LOW, released = INPUT (high impedance), never OUTPUT/HIGH.
const uint8_t BUTTON_PINS[] = {A2, A3, A4, A5};
const uint8_t BUTTON_COUNT = 4;
const unsigned long MAX_HOLD_MS = 10000;

int buttonIndex(const String &name) {
  if (name.length() != 2 || name[0] != 'K') return -1;
  int index = name[1] - '1';
  return index >= 0 && index < BUTTON_COUNT ? index : -1;
}

void setButtons(bool pressed[BUTTON_COUNT]) {
  for (uint8_t i = 0; i < BUTTON_COUNT; ++i) {
    if (pressed[i]) {
      digitalWrite(BUTTON_PINS[i], LOW);
      pinMode(BUTTON_PINS[i], OUTPUT);
    } else {
      pinMode(BUTTON_PINS[i], INPUT);
    }
  }
}

bool parseDuration(const String &value, unsigned long &duration) {
  long parsed = value.toInt();
  if (parsed <= 0 || parsed > (long)MAX_HOLD_MS) return false;
  duration = (unsigned long)parsed;
  return true;
}

void runPress(const String &buttons, unsigned long duration) {
  bool pressed[BUTTON_COUNT] = {false, false, false, false};
  int start = 0;
  while (start < buttons.length()) {
    int end = buttons.indexOf('+', start);
    if (end < 0) end = buttons.length();
    int index = buttonIndex(buttons.substring(start, end));
    if (index < 0) {
      Serial.println("ERR BUTTON");
      return;
    }
    pressed[index] = true;
    start = end + 1;
  }

  setButtons(pressed);
  delay(duration);
  bool released[BUTTON_COUNT] = {false, false, false, false};
  setButtons(released);
  Serial.print("OK ");
  Serial.print(buttons);
  Serial.print(" ");
  Serial.println(duration);
}

void handleCommand(String command) {
  command.trim();
  command.toUpperCase();
  if (command == "PING") {
    Serial.println("PONG");
    return;
  }
  if (command == "STATUS") {
    Serial.println("READY");
    return;
  }
  if (command == "STOP") {
    bool released[BUTTON_COUNT] = {false, false, false, false};
    setButtons(released);
    Serial.println("OK STOP");
    return;
  }

  int firstSpace = command.indexOf(' ');
  int secondSpace = firstSpace < 0 ? -1 : command.indexOf(' ', firstSpace + 1);
  String verb = firstSpace < 0 ? command : command.substring(0, firstSpace);
  String buttons = secondSpace < 0 ? "" : command.substring(firstSpace + 1, secondSpace);
  String durationText = secondSpace < 0 ? "" : command.substring(secondSpace + 1);
  unsigned long duration = 0;
  if ((verb != "PRESS" && verb != "HOLD") || !parseDuration(durationText, duration)) {
    Serial.println("ERR COMMAND");
    return;
  }
  runPress(buttons, duration);
}

void setup() {
  for (uint8_t pin : BUTTON_PINS) {
    pinMode(pin, INPUT);
  }
  Serial.begin(115200);
  Serial.println("BUTTON_STIMULATOR v1 READY");
}

void loop() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    handleCommand(command);
  }
}
