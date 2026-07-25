#include "zones.h"

#include "config.h"
#include "logger.h"

namespace {

const uint8_t PINS[ZONE_COUNT] = {PIN_RELAY_HERBS, PIN_RELAY_BEDS};
const char *NAMES[ZONE_COUNT] = {"herbs", "beds"};
ZoneState states[ZONE_COUNT];

} // namespace

void Zones::begin() {
  // Failsafe: Relais sofort AUS, bevor irgendwas anderes passiert
  for (uint8_t i = 0; i < ZONE_COUNT; i++) {
    pinMode(PINS[i], OUTPUT);
    digitalWrite(PINS[i], LOW);
  }
}

void Zones::loop() {
  time_t now = time(nullptr);
  for (uint8_t i = 0; i < ZONE_COUNT; i++) {
    if (!states[i].active) continue;
    if (now - states[i].startedAt >= (time_t)states[i].durationS) {
      stop(i, "completed");
    }
  }
}

bool Zones::start(uint8_t zone, uint32_t durationS, const char *cause) {
  if (zone >= ZONE_COUNT || states[zone].active || durationS == 0) return false;
  if (durationS > MAX_WATER_SECONDS) durationS = MAX_WATER_SECONDS;

  ZoneState &s = states[zone];
  s.active = true;
  s.startedAt = time(nullptr);
  s.durationS = durationS;
  strlcpy(s.cause, cause, sizeof(s.cause));

  digitalWrite(PINS[zone], HIGH);
  Logger::event("water_start", NAMES[zone], cause, durationS);
  return true;
}

bool Zones::stop(uint8_t zone, const char *reason) {
  if (zone >= ZONE_COUNT || !states[zone].active) return false;

  digitalWrite(PINS[zone], LOW);

  ZoneState &s = states[zone];
  time_t now = time(nullptr);
  uint32_t ranFor = (uint32_t)(now - s.startedAt);
  s.active = false;
  s.lastRunEnd = now;
  s.lastRunDurationS = ranFor;

  Logger::event("water_end", NAMES[zone], s.cause, ranFor, NAN, reason);
  return true;
}

const ZoneState &Zones::state(uint8_t zone) { return states[zone]; }

uint32_t Zones::remainingS(uint8_t zone) {
  const ZoneState &s = states[zone];
  if (!s.active) return 0;
  time_t elapsed = time(nullptr) - s.startedAt;
  if (elapsed >= (time_t)s.durationS) return 0;
  return s.durationS - (uint32_t)elapsed;
}

const char *Zones::name(uint8_t zone) {
  return zone < ZONE_COUNT ? NAMES[zone] : "?";
}

int8_t Zones::indexFromName(const char *name) {
  if (!name) return -1;
  for (uint8_t i = 0; i < ZONE_COUNT; i++) {
    if (strcmp(name, NAMES[i]) == 0) return i;
  }
  return -1;
}
