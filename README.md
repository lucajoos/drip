# drip

Firmware für ein 2-Zonen-Bewässerungssystem auf Basis eines LoLin NodeMCU V3 (ESP8266).
Steuert zwei 12V-Magnetventile über 3V-Relais-Module, mit Gießplänen, Regen-Skip via
Open-Meteo, Logs und REST-API (iOS-Companion-App und Home Assistant).

- **Zone `herbs`**: Kräuter + Tomaten
- **Zone `beds`**: Beete

## Features

- Beliebig viele Gießpläne: täglich, alle n Tage oder an bestimmten Wochentagen
- Regen-Skip pro Schedule mit einstellbarem Schwellwert (Open-Meteo, kein API-Key nötig)
- Logs aller Gießvorgänge und Skips (JSON, mit Rotation im Flash)
- Live-Status: welche Zone gießt gerade, Restzeit, nächster geplanter Lauf
- Manuelles Gießen/Stoppen per API
- Zeit via NTP (Zeitzone Europe/Berlin inkl. Sommerzeit), DS3231 als Fallback --
  gießt auch bei Internet-Ausfall zuverlässig weiter
- Failsafe: Ventile sind stromlos geschlossen; hartes Limit von 45 min pro Gießvorgang
- Home Assistant Custom Integration (lokales Polling der REST-API)

## Hardware & Verdrahtung

Komponenten: LoLin NodeMCU V3, 2x 3V-Relais-Modul (Optokoppler, High-Level-Trigger),
DS3231 RTC, LM2596 Step-Down-Modul, 12V-Netzteil, 2x 12V-Magnetventil.

### Stromversorgung

| Von | Nach |
|---|---|
| Netzteil 12V + | LM2596 IN+ und Relais 1+2 COM |
| Netzteil − | LM2596 IN− und gemeinsame Masse |
| LM2596 OUT+ (**vorher auf 5.0V einstellen!**) | NodeMCU VIN |
| LM2596 OUT− | NodeMCU GND |

### Steuerseite

| NodeMCU | Ziel |
|---|---|
| 3.3V | Relais 1 VCC, Relais 2 VCC, DS3231 VCC |
| GND | Relais 1 GND, Relais 2 GND, DS3231 GND |
| D1 | Relais 1 IN (Zone herbs) |
| D2 | Relais 2 IN (Zone beds) |
| D5 | DS3231 SCL |
| D6 | DS3231 SDA |

### Lastseite (pro Relais)

| Relais-Klemme | Anschluss |
|---|---|
| COM | 12V+ |
| NO | Ventil + |
| NC | frei |

Ventil − an die gemeinsame Masse. **NO verwenden, nicht NC** – so ist das Ventil
stromlos geschlossen, egal was mit dem Controller passiert.

**Gemeinsame Masse:** Netzteil −, LM2596 IN−/OUT−, NodeMCU GND, Relais-GND und
Ventil − müssen alle verbunden sein.

Beim Flashen per USB das 12V-Netzteil abziehen. In den DS3231 eine Knopfzelle
(CR2032/LIR2032) einlegen.

## Flashen

```bash
# PlatformIO installieren (einmalig)
pipx install platformio

# Zugangsdaten konfigurieren
cp include/secrets.example.h include/secrets.h
# secrets.h ausfuellen: WLAN, API-Key (openssl rand -hex 24), Standort-Koordinaten

# Bauen + Flashen (NodeMCU per USB anschliessen)
pio run -t upload

# Serielle Ausgabe ansehen (optional)
pio device monitor
```

Falls der NodeMCU nicht als Port auftaucht: anderes USB-Kabel probieren (viele
sind reine Ladekabel). Der CH340-Treiber ist in aktuellem macOS enthalten.

## REST-API

Basis-URL im lokalen Netz: `http://drip.local` (oder die IP aus dem seriellen Monitor).
Alle `/api/*`-Endpoints erwarten den Header `X-API-Key: <API_KEY aus secrets.h>`.

### Status

```bash
curl -H "X-API-Key: $KEY" http://drip.local/api/status
```

```json
{
  "time": "2026-07-25T14:30:00",
  "timeSource": "ntp",
  "rtcPresent": true,
  "uptimeS": 4223,
  "rssi": -61,
  "freeHeap": 34000,
  "zones": [
    {
      "zone": "herbs",
      "active": true,
      "cause": "schedule",
      "remainingS": 312,
      "lastRunEnd": "2026-07-25T05:10:00",
      "lastRunDurationS": 600,
      "lastScheduledRun": "2026-07-25T05:00:00",
      "nextScheduledRun": "2026-07-25T19:00:00"
    }
  ]
}
```

### Schedules

```bash
# Alle anzeigen
curl -H "X-API-Key: $KEY" http://drip.local/api/schedules

# Anlegen: taeglich 5:00, 10 Minuten, Skip ab 5 mm Regen
curl -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"zone":"herbs","time":"05:00","rhythm":"daily","durationMin":10,
       "rainSkip":{"enabled":true,"thresholdMm":5}}' \
  http://drip.local/api/schedules

# Alle 2 Tage um 19:00 (ankert am Tag der Erstellung)
curl -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"zone":"beds","time":"19:00","rhythm":"every_n_days","n":2,"durationMin":20}' \
  http://drip.local/api/schedules

# Nur Mo/Mi/Fr um 6:30
curl -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"zone":"beds","time":"06:30","rhythm":"weekdays","weekdays":["mon","wed","fri"],"durationMin":15}' \
  http://drip.local/api/schedules

# Aendern (kompletter Body wie beim Anlegen) / Loeschen
curl -X PUT -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{...}' \
  http://drip.local/api/schedules/3
curl -X DELETE -H "X-API-Key: $KEY" http://drip.local/api/schedules/3
```

Felder: `zone` (`herbs`|`beds`), `time` (`HH:MM`), `rhythm` (`daily`|`every_n_days`|`weekdays`),
`n` (1..30, nur bei `every_n_days`), `weekdays` (Array aus `mon`..`sun`, nur bei `weekdays`),
`durationMin` (1..45), `enabled` (default `true`), `rainSkip.enabled` + `rainSkip.thresholdMm`.

### Manuell gießen / stoppen

```bash
curl -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"zone":"herbs","durationMin":5}' http://drip.local/api/water

curl -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"zone":"herbs"}' http://drip.local/api/stop
```

### Logs & Wetter

```bash
curl -H "X-API-Key: $KEY" "http://drip.local/api/logs?limit=50"
curl -H "X-API-Key: $KEY" http://drip.local/api/weather
```

Log-Events: `boot`, `water_start`, `water_end`, `skip_rain` (mit `precipMm`),
`skip_busy`, `weather_error`, `error`, `schedule_created`.

## Home Assistant

Custom Integration unter [`custom_components/drip`](custom_components/drip): Home Assistant OS
im gleichen LAN spricht HTTP gegen `http://drip.local` (oder eine feste IP) mit
Header `X-API-Key`. Firmware bleibt unverändert.

### Installation (HA OS)

1. Ordner `custom_components/drip` nach `/config/custom_components/drip` kopieren
   (Samba- oder SSH-Addon). Alternativ in HACS als Custom Repository
   `lucajoos/drip` (Kategorie Integration) hinzufügen.
2. Home Assistant neu starten.
3. Einstellungen → Geräte & Dienste → Integration hinzufügen → **Drip**.
4. Host `drip.local` (oder die IP aus dem seriellen Monitor / DHCP-Reservation),
   Port `80`, API-Key aus `include/secrets.h` (`API_KEY`).

`.local` hängt an mDNS. Wenn die Auflösung in HA OS hakt, am Router eine
DHCP-Reservation setzen und die IP eintragen.

### Entities

Ein Device **Drip**, zwei Zonen analog zur iOS-App. Die Entity-IDs vergibt Home
Assistant aus Gerätename + Anzeigename (deutsche UI):

- `switch.drip_krauter` / `switch.drip_beete` — an startet `POST /api/water`
  mit der Dauer aus dem Number-Entity; aus ruft `POST /api/stop`
- Number-Entities für manuelle Gießdauer 1–45 min (nur in HA, Default 10)
- Restzeit, nächster/letzter Lauf, Ursache, RSSI, Uptime, Zeitquelle, RTC, Regen
- Gießpläne-Sensor `sensor.drip_giessplane` (Attribut `schedules`)

Exakte IDs: Entwicklerwerkzeuge → Zustände, Filter `drip`. Alte IDs mit
`aussen_drip_` nach Neuinstallation in den Entitäten aufräumen.

Status wird alle 15 s gepollt, während eine Zone gießt alle 5 s. Schedules etwa
jede Minute, Wetter alle 5 min; nach einem Service-Call sofort.

### Gießpläne

Die Integration lädt die Lovelace-Karte `custom:drip-schedules-card` und trägt
sie in den Dashboard-Ressourcen ein. Damit lassen sich Pläne direkt im Dashboard
anlegen, bearbeiten, ein-/ausschalten und löschen — analog zur iOS-App.

```yaml
type: custom:drip-schedules-card
entity: sensor.drip_giessplane
```

Nur **eine** `type:`-Zeile, wenn du über **Karte hinzufügen** gehst. Den ganzen
Block inkl. `views:` nur in der **Rohkonfiguration des Dashboards** einfügen
(siehe [`homeassistant/lovelace-drip.yaml`](homeassistant/lovelace-drip.yaml)).

Die Integration kopiert die Karte nach `/config/www/drip/` und lädt sie als
`/local/drip/drip-schedules-card.js`. Nach dem Update: HA neu starten, Browser
hart neu laden. Falls die Karte weiter „does not exist“ zeigt: Einstellungen →
Dashboards → Ressourcen → Hinzufügen, URL `/local/drip/drip-schedules-card.js`,
Typ JavaScript-Modul.

API-Client-Tests (ohne Home Assistant): `pip install -r requirements-dev.txt && pytest`

## Regen-Skip

Feuert ein Schedule mit aktivem `rainSkip`, wird Open-Meteo abgefragt:
Niederschlag der letzten 24 h plus Vorhersage der nächsten 12 h. Liegt die Summe
über `thresholdMm`, wird der Lauf übersprungen und geloggt. Ist die Wetter-API
nicht erreichbar, wird **trotzdem gegossen** (fail-open) – lieber einmal zu viel
als vertrocknete Beete im Urlaub.

## Fernzugriff im Urlaub

Der NodeMCU selbst kann kein ngrok o.ä. ausführen. Zwei Optionen:

**Option A – VPN (empfohlen):** Tailscale oder WireGuard auf dem Router (z.B.
FritzBox ab OS 7.50 kann WireGuard nativ) oder einem dauerhaft laufenden Gerät
zuhause. Vom Handy aus ins Heimnetz verbinden, dann `http://drip.local` wie gewohnt
nutzen. Die API bleibt komplett privat.

**Option B – Port-Forwarding:** Im Router einen externen Port (z.B. 47380) auf
Port 80 des NodeMCU weiterleiten. Dann schützt **nur der API-Key** und der Verkehr
ist unverschlüsselt (HTTPS ist auf dem ESP8266 als Server praktisch nicht machbar).
Nur mit langem zufälligem Key (`openssl rand -hex 24`) verwenden. Bei wechselnder
IP hilft DynDNS (FritzBox: MyFRITZ).

## Verhalten bei Ausfällen

- **Stromausfall:** Ventile schließen sofort (stromlos zu). Nach Reboot sind
  Schedules und Logs aus dem Flash wieder da; verpasste Gießzeiten werden nicht
  nachgeholt, der nächste reguläre Lauf findet normal statt.
- **WLAN/Internet weg:** Zeit läuft über den DS3231 weiter, Schedules feuern
  normal. Nur API-Zugriff und Regen-Skip (fail-open) sind betroffen.
- **Hängendes Ventil unmöglich:** jeder Gießvorgang endet spätestens nach 45 min.
