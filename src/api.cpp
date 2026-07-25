#include "api.h"

#include <ArduinoJson.h>
#include <ESP8266WebServer.h>
#include <ESP8266WiFi.h>
#include <uri/UriBraces.h>

#include "config.h"
#include "logger.h"
#include "schedules.h"
#include "secrets.h"
#include "time_service.h"
#include "weather.h"
#include "zones.h"

namespace {

ESP8266WebServer server(HTTP_PORT);

bool checkAuth() {
  if (server.header("X-API-Key") == API_KEY) return true;
  server.send(401, "application/json", "{\"error\":\"unauthorized\"}");
  return false;
}

void sendJson(int code, const JsonDocument &doc) {
  String out;
  serializeJson(doc, out);
  server.send(code, "application/json", out);
}

void sendError(int code, const String &msg) {
  JsonDocument doc;
  doc["error"] = msg;
  sendJson(code, doc);
}

bool parseBody(JsonDocument &doc) {
  DeserializationError e = deserializeJson(doc, server.arg("plain"));
  if (e) {
    sendError(400, String("json: ") + e.c_str());
    return false;
  }
  return true;
}

void isoOrNull(JsonObject obj, const char *key, time_t t) {
  if (t == 0) {
    obj[key] = nullptr;
    return;
  }
  struct tm lt;
  localtime_r(&t, &lt);
  char buf[24];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S", &lt);
  obj[key] = buf;
}

// --- Handler ---

void handleStatus() {
  if (!checkAuth()) return;

  JsonDocument doc;
  struct tm now;
  if (TimeService::localNow(now)) {
    char buf[24];
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S", &now);
    doc["time"] = buf;
  } else {
    doc["time"] = nullptr;
  }
  doc["timeSource"] = TimeService::source();
  doc["rtcPresent"] = TimeService::rtcPresent();
  doc["uptimeS"] = millis() / 1000;
  doc["rssi"] = WiFi.RSSI();
  doc["freeHeap"] = ESP.getFreeHeap();

  JsonArray zones = doc["zones"].to<JsonArray>();
  for (uint8_t z = 0; z < ZONE_COUNT; z++) {
    const ZoneState &st = Zones::state(z);
    JsonObject obj = zones.add<JsonObject>();
    obj["zone"] = Zones::name(z);
    obj["active"] = st.active;
    if (st.active) {
      obj["cause"] = st.cause;
      obj["remainingS"] = Zones::remainingS(z);
      obj["durationS"] = st.durationS;
    }
    isoOrNull(obj, "lastRunEnd", st.lastRunEnd);
    if (st.lastRunEnd > 0) obj["lastRunDurationS"] = st.lastRunDurationS;
    isoOrNull(obj, "lastScheduledRun", Schedules::lastRunForZone(z));
    isoOrNull(obj, "nextScheduledRun", Schedules::nextRunForZone(z));
  }
  sendJson(200, doc);
}

void handleListSchedules() {
  if (!checkAuth()) return;
  JsonDocument doc;
  JsonArray arr = doc.to<JsonArray>();
  time_t now = time(nullptr);
  for (size_t i = 0; i < Schedules::capacity(); i++) {
    Schedule *s = Schedules::slot(i);
    if (!s->used) continue;
    JsonObject obj = arr.add<JsonObject>();
    Schedules::toJson(*s, obj);
    isoOrNull(obj, "lastRun", s->lastRun);
    isoOrNull(obj, "nextRun", Schedules::nextRun(*s, now));
  }
  sendJson(200, doc);
}

void handleCreateSchedule() {
  if (!checkAuth()) return;
  JsonDocument body;
  if (!parseBody(body)) return;

  Schedule *s = Schedules::allocate();
  if (!s) {
    sendError(507, "max. Anzahl Schedules erreicht");
    return;
  }
  String err;
  if (!Schedules::fromJson(body.as<JsonObjectConst>(), *s, err)) {
    Schedules::remove(s->id);
    sendError(400, err);
    return;
  }
  Schedules::save();
  Logger::event("schedule_created", Zones::name(s->zone));

  JsonDocument doc;
  JsonObject obj = doc.to<JsonObject>();
  Schedules::toJson(*s, obj);
  isoOrNull(obj, "nextRun", Schedules::nextRun(*s, time(nullptr)));
  sendJson(201, doc);
}

void handleUpdateSchedule() {
  if (!checkAuth()) return;
  uint32_t id = server.pathArg(0).toInt();
  Schedule *s = Schedules::find(id);
  if (!s) {
    sendError(404, "schedule nicht gefunden");
    return;
  }
  JsonDocument body;
  if (!parseBody(body)) return;

  Schedule updated = *s;
  String err;
  if (!Schedules::fromJson(body.as<JsonObjectConst>(), updated, err)) {
    sendError(400, err);
    return;
  }
  *s = updated;
  Schedules::save();

  JsonDocument doc;
  JsonObject obj = doc.to<JsonObject>();
  Schedules::toJson(*s, obj);
  isoOrNull(obj, "nextRun", Schedules::nextRun(*s, time(nullptr)));
  sendJson(200, doc);
}

void handleDeleteSchedule() {
  if (!checkAuth()) return;
  uint32_t id = server.pathArg(0).toInt();
  if (!Schedules::remove(id)) {
    sendError(404, "schedule nicht gefunden");
    return;
  }
  server.send(204, "application/json", "");
}

void handleWater() {
  if (!checkAuth()) return;
  JsonDocument body;
  if (!parseBody(body)) return;

  int8_t zone = Zones::indexFromName(body["zone"]);
  if (zone < 0) {
    sendError(400, "zone muss 'herbs' oder 'beds' sein");
    return;
  }
  int duration = body["durationMin"] | 0;
  if (duration < 1 || duration * 60 > MAX_WATER_SECONDS) {
    sendError(400, "durationMin muss 1..45 sein");
    return;
  }
  if (!Zones::start((uint8_t)zone, (uint32_t)duration * 60, "manual")) {
    sendError(409, "zone giesst bereits");
    return;
  }
  JsonDocument doc;
  doc["zone"] = Zones::name((uint8_t)zone);
  doc["durationS"] = duration * 60;
  sendJson(200, doc);
}

void handleStop() {
  if (!checkAuth()) return;
  JsonDocument body;
  if (!parseBody(body)) return;

  int8_t zone = Zones::indexFromName(body["zone"]);
  if (zone < 0) {
    sendError(400, "zone muss 'herbs' oder 'beds' sein");
    return;
  }
  if (!Zones::stop((uint8_t)zone, "manual_stop")) {
    sendError(409, "zone giesst gerade nicht");
    return;
  }
  server.send(204, "application/json", "");
}

void handleLogs() {
  if (!checkAuth()) return;
  size_t limit = 50;
  if (server.hasArg("limit")) limit = server.arg("limit").toInt();
  server.send(200, "application/json", Logger::tail(limit));
}

void handleWeather() {
  if (!checkAuth()) return;
  const WeatherData &w = WeatherSvc::get();
  JsonDocument doc;
  doc["ok"] = w.ok;
  if (w.ok) {
    doc["past24Mm"] = serialized(String(w.past24Mm, 1));
    doc["next12Mm"] = serialized(String(w.next12Mm, 1));
  } else {
    doc["error"] = w.error;
  }
  JsonObject obj = doc.as<JsonObject>();
  isoOrNull(obj, "fetchedAt", w.fetchedAt);
  sendJson(200, doc);
}

} // namespace

void Api::begin() {
  // ESP8266WebServer sammelt nur explizit registrierte Header
  server.collectHeaders("X-API-Key");

  server.on("/", HTTP_GET, []() {
    server.send(200, "text/plain", "drip irrigation controller");
  });
  server.on("/api/status", HTTP_GET, handleStatus);
  server.on("/api/schedules", HTTP_GET, handleListSchedules);
  server.on("/api/schedules", HTTP_POST, handleCreateSchedule);
  server.on(UriBraces("/api/schedules/{}"), HTTP_PUT, handleUpdateSchedule);
  server.on(UriBraces("/api/schedules/{}"), HTTP_DELETE, handleDeleteSchedule);
  server.on("/api/water", HTTP_POST, handleWater);
  server.on("/api/stop", HTTP_POST, handleStop);
  server.on("/api/logs", HTTP_GET, handleLogs);
  server.on("/api/weather", HTTP_GET, handleWeather);
  server.onNotFound([]() { sendError(404, "not found"); });

  server.begin();
}

void Api::loop() { server.handleClient(); }
