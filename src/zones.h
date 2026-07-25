#pragma once
#include <Arduino.h>
#include <time.h>

#define ZONE_COUNT 2

struct ZoneState {
  bool active = false;
  time_t startedAt = 0;
  uint32_t durationS = 0;
  char cause[12] = ""; // "schedule" | "manual"
  time_t lastRunEnd = 0;
  uint32_t lastRunDurationS = 0;
};

namespace Zones {

void begin();
void loop();

// startet einen Giessvorgang; false wenn Zone schon aktiv
bool start(uint8_t zone, uint32_t durationS, const char *cause);
// stoppt; reason landet im Log ("completed" | "manual_stop")
bool stop(uint8_t zone, const char *reason);

const ZoneState &state(uint8_t zone);
uint32_t remainingS(uint8_t zone);

const char *name(uint8_t zone);          // "herbs" | "beds"
int8_t indexFromName(const char *name); // -1 wenn unbekannt

} // namespace Zones
