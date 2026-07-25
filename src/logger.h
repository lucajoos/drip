#pragma once
#include <Arduino.h>

namespace Logger {

void begin();

// Schreibt eine JSON-Zeile ins Log. Optionale Felder werden weggelassen,
// wenn nullptr / negativ / NAN.
void event(const char *type, const char *zone = nullptr,
           const char *cause = nullptr, long durationS = -1,
           float precipMm = NAN, const char *note = nullptr);

// Neueste `limit` Eintraege als JSON-Array-String (neueste zuerst).
String tail(size_t limit);

} // namespace Logger
