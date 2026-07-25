#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <ESP8266mDNS.h>
#include <LittleFS.h>

#include "api.h"
#include "config.h"
#include "logger.h"
#include "schedules.h"
#include "secrets.h"
#include "status_led.h"
#include "time_service.h"
#include "weather.h"
#include "zones.h"

namespace {

bool mdnsStarted = false;

void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.hostname(HOSTNAME);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
}

} // namespace

void setup() {
  // Ventile zuerst sicher schliessen, alles andere danach
  Zones::begin();

  Serial.begin(115200);
  Serial.println();
  Serial.println(F("drip startet..."));

  LittleFS.begin();
  StatusLed::begin();
  connectWifi();
  TimeService::begin();
  Logger::begin();
  Schedules::begin();
  Api::begin();

  Serial.println(F("bereit"));
}

void loop() {
  Api::loop();
  Zones::loop();
  Schedules::loop();
  TimeService::loop();
  StatusLed::loop();

  static bool wasConnected = false;
  if (WiFi.status() == WL_CONNECTED && !wasConnected) {
    wasConnected = true;
    Serial.print(F("wlan verbunden: "));
    Serial.println(WiFi.localIP());
    mdnsStarted = MDNS.begin(HOSTNAME);
    if (mdnsStarted) MDNS.addService("http", "tcp", HTTP_PORT);
  }
  if (mdnsStarted) MDNS.update();
}
