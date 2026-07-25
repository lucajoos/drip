#include "status_led.h"

#include <Arduino.h>
#include <ESP8266WiFi.h>

#include "config.h"
#include "time_service.h"

namespace {

// LED ist active-low
void ledOn(bool on) { digitalWrite(PIN_STATUS_LED, on ? LOW : HIGH); }

} // namespace

void StatusLed::begin() {
  pinMode(PIN_STATUS_LED, OUTPUT);
  ledOn(false);
}

void StatusLed::loop() {
  if (WiFi.status() != WL_CONNECTED) {
    ledOn((millis() / 150) % 2 == 0);
  } else if (!TimeService::timeValid()) {
    ledOn((millis() / 700) % 2 == 0);
  } else {
    ledOn(true);
  }
}
