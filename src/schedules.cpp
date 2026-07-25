#include "schedules.h"

#include <LittleFS.h>

#include "config.h"
#include "logger.h"
#include "time_service.h"
#include "weather.h"
#include "zones.h"

namespace {

Schedule schedules[MAX_SCHEDULES];
uint32_t nextId = 1;
unsigned long lastTickMs = 0;

const char *WEEKDAY_NAMES[7] = {"sun", "mon", "tue", "wed",
                                "thu", "fri", "sat"};

// Tage seit 1970-01-01 aus Kalenderdatum (DST-sicher, Howard Hinnant)
uint32_t daysFromCivil(int y, unsigned m, unsigned d) {
  y -= m <= 2;
  const int era = (y >= 0 ? y : y - 399) / 400;
  const unsigned yoe = (unsigned)(y - era * 400);
  const unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
  const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
  return (uint32_t)(era * 146097 + (int)doe + 719468);
}

uint32_t localDayOf(const struct tm &t) {
  return daysFromCivil(t.tm_year + 1900, t.tm_mon + 1, t.tm_mday);
}

bool rhythmMatchesDay(const Schedule &s, const struct tm &day) {
  switch (s.rhythm) {
    case Rhythm::Daily:
      return true;
    case Rhythm::Weekdays:
      return s.weekdayMask & (1 << day.tm_wday);
    case Rhythm::EveryNDays: {
      uint32_t today = localDayOf(day);
      if (s.n == 0 || today < s.anchorDay) return false;
      return (today - s.anchorDay) % s.n == 0;
    }
  }
  return false;
}

const char *rhythmName(Rhythm r) {
  switch (r) {
    case Rhythm::Daily: return "daily";
    case Rhythm::EveryNDays: return "every_n_days";
    case Rhythm::Weekdays: return "weekdays";
  }
  return "daily";
}

void load() {
  File f = LittleFS.open(SCHEDULES_FILE, "r");
  if (!f) return;
  JsonDocument doc;
  DeserializationError e = deserializeJson(doc, f);
  f.close();
  if (e) {
    Logger::event("error", nullptr, nullptr, -1, NAN, "schedules.json defekt");
    return;
  }

  nextId = doc["nextId"] | 1;
  size_t i = 0;
  for (JsonObjectConst obj : doc["items"].as<JsonArrayConst>()) {
    if (i >= MAX_SCHEDULES) break;
    Schedule &s = schedules[i];
    String err;
    if (!Schedules::fromJson(obj, s, err)) continue;
    s.used = true;
    s.id = obj["id"] | 0;
    s.anchorDay = obj["anchorDay"] | s.anchorDay;
    s.lastRun = (time_t)(obj["lastRun"] | 0);
    if (s.id == 0) s.id = nextId++;
    i++;
  }
}

// Regen pruefen und ggf. giessen; laeuft genau einmal pro Occurrence
void fire(Schedule &s, time_t occ) {
  s.lastRun = occ;
  Schedules::save();

  const char *zoneName = Zones::name(s.zone);

  if (s.rainSkipEnabled) {
    const WeatherData &w = WeatherSvc::get();
    if (w.ok) {
      float total = w.past24Mm + w.next12Mm;
      if (total >= s.rainThresholdMm) {
        Logger::event("skip_rain", zoneName, "schedule", -1, total);
        return;
      }
    } else {
      // fail-open: lieber giessen als vertrocknen
      Logger::event("weather_error", zoneName, "schedule", -1, NAN,
                    w.error.c_str());
    }
  }

  if (!Zones::start(s.zone, (uint32_t)s.durationMin * 60, "schedule")) {
    Logger::event("skip_busy", zoneName, "schedule");
  }
}

} // namespace

void Schedules::begin() { load(); }

void Schedules::loop() {
  if (millis() - lastTickMs < 10000) return;
  lastTickMs = millis();

  struct tm now;
  if (!TimeService::localNow(now)) return;

  time_t nowEpoch = time(nullptr);

  for (size_t i = 0; i < MAX_SCHEDULES; i++) {
    Schedule &s = schedules[i];
    if (!s.used || !s.enabled) continue;
    if (!rhythmMatchesDay(s, now)) continue;

    struct tm occTm = now;
    occTm.tm_hour = s.hour;
    occTm.tm_min = s.minute;
    occTm.tm_sec = 0;
    occTm.tm_isdst = -1;
    time_t occ = mktime(&occTm);

    // 2-Minuten-Fenster: verpasste Occurrences (Reboot, Stromausfall)
    // werden nicht nachgeholt
    if (nowEpoch >= occ && nowEpoch < occ + 120 && s.lastRun < occ) {
      fire(s, occ);
    }
  }
}

Schedule *Schedules::find(uint32_t id) {
  for (size_t i = 0; i < MAX_SCHEDULES; i++) {
    if (schedules[i].used && schedules[i].id == id) return &schedules[i];
  }
  return nullptr;
}

Schedule *Schedules::allocate() {
  for (size_t i = 0; i < MAX_SCHEDULES; i++) {
    if (!schedules[i].used) {
      schedules[i] = Schedule();
      schedules[i].used = true;
      schedules[i].id = nextId++;
      return &schedules[i];
    }
  }
  return nullptr;
}

bool Schedules::remove(uint32_t id) {
  Schedule *s = find(id);
  if (!s) return false;
  s->used = false;
  save();
  return true;
}

void Schedules::save() {
  JsonDocument doc;
  doc["nextId"] = nextId;
  JsonArray items = doc["items"].to<JsonArray>();
  for (size_t i = 0; i < MAX_SCHEDULES; i++) {
    if (!schedules[i].used) continue;
    JsonObject obj = items.add<JsonObject>();
    toJson(schedules[i], obj);
    obj["anchorDay"] = schedules[i].anchorDay;
    obj["lastRun"] = (uint32_t)schedules[i].lastRun;
  }
  File f = LittleFS.open(SCHEDULES_FILE, "w");
  if (!f) {
    Logger::event("error", nullptr, nullptr, -1, NAN,
                  "schedules.json schreiben fehlgeschlagen");
    return;
  }
  serializeJson(doc, f);
  f.close();
}

size_t Schedules::capacity() { return MAX_SCHEDULES; }

Schedule *Schedules::slot(size_t i) {
  return i < MAX_SCHEDULES ? &schedules[i] : nullptr;
}

void Schedules::toJson(const Schedule &s, JsonObject obj) {
  obj["id"] = s.id;
  obj["zone"] = Zones::name(s.zone);
  char buf[8];
  snprintf(buf, sizeof(buf), "%02u:%02u", s.hour, s.minute);
  obj["time"] = buf;
  obj["rhythm"] = rhythmName(s.rhythm);
  if (s.rhythm == Rhythm::EveryNDays) obj["n"] = s.n;
  if (s.rhythm == Rhythm::Weekdays) {
    JsonArray days = obj["weekdays"].to<JsonArray>();
    for (uint8_t d = 0; d < 7; d++) {
      if (s.weekdayMask & (1 << d)) days.add(WEEKDAY_NAMES[d]);
    }
  }
  obj["durationMin"] = s.durationMin;
  obj["enabled"] = s.enabled;
  JsonObject rain = obj["rainSkip"].to<JsonObject>();
  rain["enabled"] = s.rainSkipEnabled;
  rain["thresholdMm"] = serialized(String(s.rainThresholdMm, 1));
}

bool Schedules::fromJson(JsonObjectConst obj, Schedule &s, String &err) {
  const char *zoneName = obj["zone"];
  int8_t zone = Zones::indexFromName(zoneName);
  if (zone < 0) {
    err = "zone muss 'herbs' oder 'beds' sein";
    return false;
  }

  const char *timeStr = obj["time"];
  unsigned h = 0, m = 0;
  if (!timeStr || sscanf(timeStr, "%2u:%2u", &h, &m) != 2 || h > 23 || m > 59) {
    err = "time muss Format 'HH:MM' haben";
    return false;
  }

  const char *rhythmStr = obj["rhythm"] | "daily";
  Rhythm rhythm;
  uint8_t n = 1;
  uint8_t mask = 0;
  if (strcmp(rhythmStr, "daily") == 0) {
    rhythm = Rhythm::Daily;
  } else if (strcmp(rhythmStr, "every_n_days") == 0) {
    rhythm = Rhythm::EveryNDays;
    n = obj["n"] | 0;
    if (n < 1 || n > 30) {
      err = "n muss 1..30 sein";
      return false;
    }
  } else if (strcmp(rhythmStr, "weekdays") == 0) {
    rhythm = Rhythm::Weekdays;
    for (JsonVariantConst v : obj["weekdays"].as<JsonArrayConst>()) {
      const char *day = v.as<const char *>();
      for (uint8_t d = 0; d < 7; d++) {
        if (day && strcmp(day, WEEKDAY_NAMES[d]) == 0) mask |= (1 << d);
      }
    }
    if (mask == 0) {
      err = "weekdays: mind. ein Tag aus [sun,mon,tue,wed,thu,fri,sat]";
      return false;
    }
  } else {
    err = "rhythm muss daily, every_n_days oder weekdays sein";
    return false;
  }

  int duration = obj["durationMin"] | 0;
  if (duration < 1 || duration * 60 > MAX_WATER_SECONDS) {
    err = "durationMin muss 1..45 sein";
    return false;
  }

  s.zone = (uint8_t)zone;
  s.hour = (uint8_t)h;
  s.minute = (uint8_t)m;
  s.rhythm = rhythm;
  s.n = n;
  s.weekdayMask = mask;
  s.durationMin = (uint16_t)duration;
  s.enabled = obj["enabled"] | true;

  JsonObjectConst rain = obj["rainSkip"];
  s.rainSkipEnabled = rain["enabled"] | false;
  s.rainThresholdMm = rain["thresholdMm"] | 5.0f;
  if (s.rainSkipEnabled && s.rainThresholdMm <= 0) {
    err = "rainSkip.thresholdMm muss > 0 sein";
    return false;
  }

  // every_n_days ankert am Tag der Erstellung/Aenderung ("ab heute alle n Tage")
  if (rhythm == Rhythm::EveryNDays) {
    struct tm now;
    if (TimeService::localNow(now)) s.anchorDay = localDayOf(now);
  }
  return true;
}

time_t Schedules::nextRun(const Schedule &s, time_t now) {
  if (!s.used || !s.enabled) return 0;
  struct tm base;
  localtime_r(&now, &base);
  for (int d = 0; d < 62; d++) {
    struct tm day = base;
    day.tm_mday += d;
    day.tm_hour = s.hour;
    day.tm_min = s.minute;
    day.tm_sec = 0;
    day.tm_isdst = -1;
    time_t occ = mktime(&day); // normalisiert Datum + tm_wday
    if (occ <= now) continue;
    if (rhythmMatchesDay(s, day)) return occ;
  }
  return 0;
}

time_t Schedules::nextRunForZone(uint8_t zone) {
  time_t now = time(nullptr);
  time_t best = 0;
  for (size_t i = 0; i < MAX_SCHEDULES; i++) {
    const Schedule &s = schedules[i];
    if (!s.used || s.zone != zone) continue;
    time_t t = nextRun(s, now);
    if (t > 0 && (best == 0 || t < best)) best = t;
  }
  return best;
}

time_t Schedules::lastRunForZone(uint8_t zone) {
  time_t best = 0;
  for (size_t i = 0; i < MAX_SCHEDULES; i++) {
    const Schedule &s = schedules[i];
    if (!s.used || s.zone != zone) continue;
    if (s.lastRun > best) best = s.lastRun;
  }
  return best;
}

uint32_t Schedules::currentLocalDay() {
  struct tm now;
  if (!TimeService::localNow(now)) return 0;
  return localDayOf(now);
}
