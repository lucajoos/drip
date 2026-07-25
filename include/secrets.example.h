// Kopieren nach include/secrets.h und ausfuellen. secrets.h ist gitignored.
#pragma once

#define WIFI_SSID "mein-wlan"
#define WIFI_PASS "mein-passwort"

// Langer zufaelliger Key, z.B. via: openssl rand -hex 24
#define API_KEY "change-me"

// Standort fuer die Regen-Abfrage (Open-Meteo)
#define WEATHER_LATITUDE 52.5200
#define WEATHER_LONGITUDE 13.4050
