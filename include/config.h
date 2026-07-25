#pragma once

// --- Pins (LoLin NodeMCU V3) ---
// D1/D2 sind beim Booten LOW und togglen nicht -> Ventile bleiben sicher zu
// (Relais-Module sind High-Level-Trigger).
#define PIN_RELAY_HERBS D1 // GPIO5, Zone Kraeuter + Tomaten
#define PIN_RELAY_BEDS D2  // GPIO4, Zone Beete
#define PIN_I2C_SDA D6     // GPIO12, DS3231 SDA
#define PIN_I2C_SCL D5     // GPIO14, DS3231 SCL

// --- Netzwerk ---
#define HOSTNAME "drip" // erreichbar als drip.local
#define HTTP_PORT 80

// --- Zeit ---
#define TZ_EUROPE_BERLIN "CET-1CEST,M3.5.0,M10.5.0/3"
#define NTP_SERVER_1 "pool.ntp.org"
#define NTP_SERVER_2 "time.cloudflare.com"

// --- Bewaesserung ---
#define MAX_WATER_SECONDS (45 * 60) // hartes Limit pro Giessvorgang
#define MAX_SCHEDULES 16

// --- Wetter (Open-Meteo) ---
#define WEATHER_CACHE_SECONDS (30 * 60)
#define WEATHER_PAST_HOURS 24
#define WEATHER_FORECAST_HOURS 12
#define WEATHER_TIMEOUT_MS 6000

// --- Logs ---
#define LOG_FILE "/logs.jsonl"
#define LOG_FILE_OLD "/logs.old.jsonl"
#define LOG_ROTATE_BYTES 40960
#define SCHEDULES_FILE "/schedules.json"
