#pragma once
#include <Arduino.h>
#include <time.h>

namespace TimeService {

void begin();
void loop();

// true sobald die Systemzeit plausibel ist (NTP oder DS3231)
bool timeValid();
time_t nowUtc();
bool localNow(struct tm &out);

// "ntp", "rtc" oder "none"
const char *source();
bool rtcPresent();

} // namespace TimeService
