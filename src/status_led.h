#pragma once

// Onboard-LED als Verbindungsanzeige:
//   schnelles Blinken (150 ms)  -> keine WLAN-Verbindung
//   langsames Blinken (700 ms)  -> WLAN ok, aber Zeit noch nicht synchron (kein Internet/NTP und keine RTC-Zeit)
//   dauerhaft an                -> verbunden und Zeit gueltig
namespace StatusLed {

void begin();
void loop();

} // namespace StatusLed
