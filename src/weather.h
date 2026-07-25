#pragma once
#include <Arduino.h>
#include <time.h>

struct WeatherData {
  bool ok = false;
  float past24Mm = 0;   // Niederschlag letzte 24 h
  float next12Mm = 0;   // Vorhersage naechste 12 h
  time_t fetchedAt = 0;
  String error;
};

namespace WeatherSvc {

// Liefert gecachte Daten (max. WEATHER_CACHE_SECONDS alt), sonst neuer Abruf.
// Blockiert bis zu ~WEATHER_TIMEOUT_MS. Bei Fehler: ok == false (fail-open
// wird vom Aufrufer entschieden).
const WeatherData &get(bool forceRefresh = false);

} // namespace WeatherSvc
