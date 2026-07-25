#include "time_service.h"

#include <RTClib.h>
#include <Wire.h>
#include <coredecls.h> // settimeofday_cb
#include <sys/time.h>

#include "config.h"
#include "logger.h"

namespace {

RTC_DS3231 rtc;
bool rtcOk = false;
bool ntpSynced = false;
bool seededFromRtc = false;
unsigned long lastRtcWriteMs = 0;

constexpr time_t MIN_VALID_EPOCH = 1700000000; // Ende 2023

} // namespace

void TimeService::begin() {
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  rtcOk = rtc.begin();

  settimeofday_cb([](bool fromSntp) {
    if (fromSntp) ntpSynced = true;
  });

  configTime(TZ_EUROPE_BERLIN, NTP_SERVER_1, NTP_SERVER_2);

  // Kein NTP (noch) -> Systemzeit aus der RTC setzen (RTC speichert UTC)
  if (time(nullptr) < MIN_VALID_EPOCH && rtcOk) {
    DateTime dt = rtc.now();
    if ((time_t)dt.unixtime() > MIN_VALID_EPOCH) {
      timeval tv = {(time_t)dt.unixtime(), 0};
      settimeofday(&tv, nullptr);
      seededFromRtc = true;
    }
  }
}

void TimeService::loop() {
  // Nach NTP-Sync die RTC regelmaessig nachstellen (alle 6 h)
  if (ntpSynced && rtcOk &&
      (lastRtcWriteMs == 0 || millis() - lastRtcWriteMs > 6UL * 3600UL * 1000UL)) {
    rtc.adjust(DateTime((uint32_t)time(nullptr)));
    lastRtcWriteMs = millis();
  }
}

bool TimeService::timeValid() { return time(nullptr) > MIN_VALID_EPOCH; }

time_t TimeService::nowUtc() { return time(nullptr); }

bool TimeService::localNow(struct tm &out) {
  if (!timeValid()) return false;
  time_t t = time(nullptr);
  localtime_r(&t, &out);
  return true;
}

const char *TimeService::source() {
  if (ntpSynced) return "ntp";
  if (seededFromRtc && timeValid()) return "rtc";
  return "none";
}

bool TimeService::rtcPresent() { return rtcOk; }
