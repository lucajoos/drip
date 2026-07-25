#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include <time.h>

enum class Rhythm : uint8_t { Daily = 0, EveryNDays = 1, Weekdays = 2 };

struct Schedule {
  bool used = false;
  uint32_t id = 0;
  uint8_t zone = 0; // Index in Zones
  uint8_t hour = 0;
  uint8_t minute = 0;
  Rhythm rhythm = Rhythm::Daily;
  uint8_t n = 1;           // fuer every_n_days
  uint8_t weekdayMask = 0; // Bit = tm_wday (0 = Sonntag)
  uint16_t durationMin = 10;
  bool enabled = true;
  bool rainSkipEnabled = false;
  float rainThresholdMm = 5.0f;
  uint32_t anchorDay = 0; // lokale Tage seit Epoche, Anker fuer every_n_days
  time_t lastRun = 0;     // Epoch der zuletzt behandelten Occurrence
};

namespace Schedules {

void begin();
void loop();

Schedule *find(uint32_t id);
Schedule *allocate(); // freier Slot oder nullptr
bool remove(uint32_t id);
void save();
size_t capacity();
Schedule *slot(size_t i);

// JSON <-> Schedule; fromJson validiert und schreibt Fehlermeldung nach err
void toJson(const Schedule &s, JsonObject obj);
bool fromJson(JsonObjectConst obj, Schedule &s, String &err);

// naechste Ausfuehrung (Epoch) oder 0
time_t nextRun(const Schedule &s, time_t now);
time_t nextRunForZone(uint8_t zone);
time_t lastRunForZone(uint8_t zone);

uint32_t currentLocalDay();

} // namespace Schedules
