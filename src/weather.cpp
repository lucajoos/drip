#include "weather.h"

#include <ArduinoJson.h>
#include <ESP8266HTTPClient.h>
#include <ESP8266WiFi.h>
#include <WiFiClientSecureBearSSL.h>

#include "config.h"
#include "secrets.h"

namespace {

WeatherData cache;

String buildUrl(bool https) {
  String url = https ? "https" : "http";
  url += "://api.open-meteo.com/v1/forecast?latitude=";
  url += String(WEATHER_LATITUDE, 4);
  url += "&longitude=";
  url += String(WEATHER_LONGITUDE, 4);
  url += "&hourly=precipitation&past_hours=";
  url += WEATHER_PAST_HOURS;
  url += "&forecast_hours=";
  url += WEATHER_FORECAST_HOURS;
  url += "&timezone=UTC";
  return url;
}

bool parseResponse(Stream &body, WeatherData &out, String &err) {
  JsonDocument filter;
  filter["hourly"]["precipitation"] = true;

  JsonDocument doc;
  DeserializationError e =
      deserializeJson(doc, body, DeserializationOption::Filter(filter));
  if (e) {
    err = String("json: ") + e.c_str();
    return false;
  }

  JsonArrayConst precip = doc["hourly"]["precipitation"];
  if (precip.isNull()) {
    err = "json: hourly.precipitation fehlt";
    return false;
  }

  float past = 0, future = 0;
  size_t i = 0;
  for (JsonVariantConst v : precip) {
    float mm = v.isNull() ? 0.0f : v.as<float>();
    if (i < WEATHER_PAST_HOURS) past += mm;
    else future += mm;
    i++;
  }
  out.past24Mm = past;
  out.next12Mm = future;
  return true;
}

bool fetch(WeatherData &out) {
  if (WiFi.status() != WL_CONNECTED) {
    out.error = "kein wlan";
    return false;
  }

  // Erst plain HTTP (schont RAM), bei Fehlschlag HTTPS-Fallback
  for (int attempt = 0; attempt < 2; attempt++) {
    bool useTls = attempt == 1;
    HTTPClient http;
    http.setTimeout(WEATHER_TIMEOUT_MS);
    http.useHTTP10(true); // kein chunked encoding -> sauberes Stream-Parsing

    bool began;
    std::unique_ptr<BearSSL::WiFiClientSecure> tls;
    WiFiClient plain;
    if (useTls) {
      tls.reset(new BearSSL::WiFiClientSecure);
      tls->setInsecure();
      tls->setBufferSizes(4096, 512);
      began = http.begin(*tls, buildUrl(true));
    } else {
      began = http.begin(plain, buildUrl(false));
    }
    if (!began) {
      out.error = "http begin fehlgeschlagen";
      continue;
    }

    int code = http.GET();
    if (code == HTTP_CODE_OK) {
      String err;
      bool ok = parseResponse(http.getStream(), out, err);
      http.end();
      if (ok) return true;
      out.error = err;
      return false;
    }
    http.end();
    out.error = String(useTls ? "https " : "http ") + code;
  }
  return false;
}

} // namespace

const WeatherData &WeatherSvc::get(bool forceRefresh) {
  time_t now = time(nullptr);
  bool fresh = cache.ok && cache.fetchedAt > 0 &&
               (now - cache.fetchedAt) < WEATHER_CACHE_SECONDS;
  if (fresh && !forceRefresh) return cache;

  WeatherData result;
  if (fetch(result)) {
    result.ok = true;
    result.fetchedAt = now;
    cache = result;
  } else {
    cache.ok = false;
    cache.error = result.error;
    cache.fetchedAt = now;
  }
  return cache;
}
