#include "logger.h"

#include <ArduinoJson.h>
#include <LittleFS.h>
#include <time.h>

#include "config.h"

namespace {

void isoTimestamp(char *buf, size_t len) {
  time_t t = time(nullptr);
  struct tm tmLocal;
  localtime_r(&t, &tmLocal);
  strftime(buf, len, "%Y-%m-%dT%H:%M:%S", &tmLocal);
}

void rotateIfNeeded() {
  File f = LittleFS.open(LOG_FILE, "r");
  if (!f) return;
  size_t size = f.size();
  f.close();
  if (size < LOG_ROTATE_BYTES) return;
  LittleFS.remove(LOG_FILE_OLD);
  LittleFS.rename(LOG_FILE, LOG_FILE_OLD);
}

// Haengt die letzten Zeilen einer Datei an den Ringpuffer an.
void collectLines(const char *path, String *ring, size_t ringSize,
                  size_t &next, size_t &total) {
  File f = LittleFS.open(path, "r");
  if (!f) return;
  while (f.available()) {
    String line = f.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) continue;
    ring[next] = line;
    next = (next + 1) % ringSize;
    total++;
  }
  f.close();
}

} // namespace

void Logger::begin() {
  event("boot", nullptr, nullptr, -1, NAN, ESP.getResetReason().c_str());
}

void Logger::event(const char *type, const char *zone, const char *cause,
                   long durationS, float precipMm, const char *note) {
  rotateIfNeeded();

  JsonDocument doc;
  doc["ts"] = (uint32_t)time(nullptr);
  char iso[24];
  isoTimestamp(iso, sizeof(iso));
  doc["time"] = iso;
  doc["event"] = type;
  if (zone) doc["zone"] = zone;
  if (cause) doc["cause"] = cause;
  if (durationS >= 0) doc["durationS"] = durationS;
  if (!isnan(precipMm)) doc["precipMm"] = serialized(String(precipMm, 1));
  if (note) doc["note"] = note;

  File f = LittleFS.open(LOG_FILE, "a");
  if (!f) return;
  serializeJson(doc, f);
  f.print('\n');
  f.close();
}

String Logger::tail(size_t limit) {
  if (limit == 0) limit = 1;
  if (limit > 100) limit = 100;

  String *ring = new String[limit];
  size_t next = 0, total = 0;
  collectLines(LOG_FILE_OLD, ring, limit, next, total);
  collectLines(LOG_FILE, ring, limit, next, total);

  size_t count = total < limit ? total : limit;
  String out = "[";
  for (size_t i = 0; i < count; i++) {
    // Rueckwaerts ab der zuletzt geschriebenen Zeile -> neueste zuerst
    size_t idx = (next + limit - 1 - i) % limit;
    if (i > 0) out += ',';
    out += ring[idx];
  }
  out += ']';
  delete[] ring;
  return out;
}
