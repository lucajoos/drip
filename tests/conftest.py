"""Shared fixtures: in-memory fake of the drip ESP REST API."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

# Avoid executing custom_components/drip/__init__.py (Home Assistant imports)
# so API tests run without a HA install.
_DRIP_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "drip"
if "custom_components.drip" not in sys.modules:
    _pkg = types.ModuleType("custom_components.drip")
    _pkg.__path__ = [str(_DRIP_DIR)]
    _pkg.__file__ = str(_DRIP_DIR / "__init__.py")
    sys.modules["custom_components.drip"] = _pkg

import aiohttp  # noqa: E402
import pytest  # noqa: E402
from aiohttp import web  # noqa: E402

from custom_components.drip.api import DripClient  # noqa: E402

API_KEY = "test-key"


class FakeDrip:
    """Minimal ESP API used by tests."""

    def __init__(self) -> None:
        self.zones = {
            "herbs": {
                "zone": "herbs",
                "active": False,
                "lastRunEnd": None,
                "lastScheduledRun": None,
                "nextScheduledRun": "2026-07-25T19:00:00",
            },
            "beds": {
                "zone": "beds",
                "active": False,
                "lastRunEnd": "2026-07-25T05:10:00",
                "lastRunDurationS": 600,
                "lastScheduledRun": "2026-07-25T05:00:00",
                "nextScheduledRun": "2026-07-26T05:00:00",
            },
        }
        self.schedules: list[dict[str, Any]] = []
        self.next_id = 1
        self.weather = {
            "ok": True,
            "past24Mm": 1.2,
            "next12Mm": 0.4,
            "fetchedAt": "2026-07-25T14:00:00",
        }

    def _auth(self, request: web.Request) -> None:
        if request.headers.get("X-API-Key") != API_KEY:
            raise web.HTTPUnauthorized(
                text='{"error":"unauthorized"}', content_type="application/json"
            )

    async def handle_status(self, request: web.Request) -> web.Response:
        self._auth(request)
        return web.json_response(
            {
                "time": "2026-07-25T14:30:00",
                "timeSource": "ntp",
                "rtcPresent": True,
                "uptimeS": 4223,
                "rssi": -61,
                "freeHeap": 34000,
                "zones": list(self.zones.values()),
            }
        )

    async def handle_weather(self, request: web.Request) -> web.Response:
        self._auth(request)
        return web.json_response(self.weather)

    async def handle_list_schedules(self, request: web.Request) -> web.Response:
        self._auth(request)
        return web.json_response(self.schedules)

    async def handle_create_schedule(self, request: web.Request) -> web.Response:
        self._auth(request)
        body = await request.json()
        if len(self.schedules) >= 16:
            return web.json_response(
                {"error": "max. Anzahl Schedules erreicht"}, status=507
            )
        err = _validate_schedule(body)
        if err:
            return web.json_response({"error": err}, status=400)
        item = _schedule_from_body(self.next_id, body)
        self.next_id += 1
        self.schedules.append(item)
        return web.json_response(item, status=201)

    async def handle_update_schedule(self, request: web.Request) -> web.Response:
        self._auth(request)
        schedule_id = int(request.match_info["sid"])
        found = next((s for s in self.schedules if s["id"] == schedule_id), None)
        if found is None:
            return web.json_response({"error": "schedule nicht gefunden"}, status=404)
        body = await request.json()
        err = _validate_schedule(body)
        if err:
            return web.json_response({"error": err}, status=400)
        updated = _schedule_from_body(schedule_id, body)
        self.schedules[self.schedules.index(found)] = updated
        return web.json_response(updated)

    async def handle_delete_schedule(self, request: web.Request) -> web.Response:
        self._auth(request)
        schedule_id = int(request.match_info["sid"])
        found = next((s for s in self.schedules if s["id"] == schedule_id), None)
        if found is None:
            return web.json_response({"error": "schedule nicht gefunden"}, status=404)
        self.schedules.remove(found)
        return web.Response(status=204)

    async def handle_water(self, request: web.Request) -> web.Response:
        self._auth(request)
        body = await request.json()
        zone = body.get("zone")
        if zone not in self.zones:
            return web.json_response(
                {"error": "zone muss 'herbs' oder 'beds' sein"}, status=400
            )
        duration = int(body.get("durationMin") or 0)
        if duration < 1 or duration > 45:
            return web.json_response({"error": "durationMin muss 1..45 sein"}, status=400)
        state = self.zones[zone]
        if state["active"]:
            return web.json_response({"error": "zone giesst bereits"}, status=409)
        state["active"] = True
        state["cause"] = "manual"
        state["remainingS"] = duration * 60
        state["durationS"] = duration * 60
        return web.json_response({"zone": zone, "durationS": duration * 60})

    async def handle_stop(self, request: web.Request) -> web.Response:
        self._auth(request)
        body = await request.json()
        zone = body.get("zone")
        if zone not in self.zones:
            return web.json_response(
                {"error": "zone muss 'herbs' oder 'beds' sein"}, status=400
            )
        state = self.zones[zone]
        if not state["active"]:
            return web.json_response({"error": "zone giesst gerade nicht"}, status=409)
        state["active"] = False
        state.pop("cause", None)
        state.pop("remainingS", None)
        state.pop("durationS", None)
        return web.Response(status=204)


def _validate_schedule(body: dict[str, Any]) -> str | None:
    if body.get("zone") not in ("herbs", "beds"):
        return "zone muss 'herbs' oder 'beds' sein"
    time_str = body.get("time")
    if not isinstance(time_str, str) or len(time_str) < 4:
        return "time muss Format 'HH:MM' haben"
    duration = int(body.get("durationMin") or 0)
    if duration < 1 or duration > 45:
        return "durationMin muss 1..45 sein"
    rhythm = body.get("rhythm", "daily")
    if rhythm not in ("daily", "every_n_days", "weekdays"):
        return "rhythm muss daily, every_n_days oder weekdays sein"
    if rhythm == "every_n_days":
        n = int(body.get("n") or 0)
        if n < 1 or n > 30:
            return "n muss 1..30 sein"
    if rhythm == "weekdays" and not body.get("weekdays"):
        return "weekdays: mind. ein Tag aus [sun,mon,tue,wed,thu,fri,sat]"
    rain = body.get("rainSkip") or {}
    if rain.get("enabled") and float(rain.get("thresholdMm") or 0) <= 0:
        return "rainSkip.thresholdMm muss > 0 sein"
    return None


def _schedule_from_body(schedule_id: int, body: dict[str, Any]) -> dict[str, Any]:
    rain = body.get("rainSkip") or {}
    item: dict[str, Any] = {
        "id": schedule_id,
        "zone": body["zone"],
        "time": body["time"],
        "rhythm": body.get("rhythm", "daily"),
        "durationMin": body["durationMin"],
        "enabled": body.get("enabled", True),
        "rainSkip": {
            "enabled": bool(rain.get("enabled", False)),
            "thresholdMm": float(rain.get("thresholdMm", 5.0)),
        },
        "lastRun": None,
        "nextRun": "2026-07-26T05:00:00",
    }
    if item["rhythm"] == "every_n_days":
        item["n"] = body["n"]
    if item["rhythm"] == "weekdays":
        item["weekdays"] = list(body["weekdays"])
    return item


@pytest.fixture
async def fake_drip() -> FakeDrip:
    return FakeDrip()


@pytest.fixture
async def drip_client(fake_drip: FakeDrip):
    app = web.Application()
    app.router.add_get("/api/status", fake_drip.handle_status)
    app.router.add_get("/api/weather", fake_drip.handle_weather)
    app.router.add_get("/api/schedules", fake_drip.handle_list_schedules)
    app.router.add_post("/api/schedules", fake_drip.handle_create_schedule)
    app.router.add_put("/api/schedules/{sid}", fake_drip.handle_update_schedule)
    app.router.add_delete("/api/schedules/{sid}", fake_drip.handle_delete_schedule)
    app.router.add_post("/api/water", fake_drip.handle_water)
    app.router.add_post("/api/stop", fake_drip.handle_stop)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    sockets = site._server.sockets  # type: ignore[union-attr]
    port = sockets[0].getsockname()[1]
    session = aiohttp.ClientSession()
    client = DripClient(session, "127.0.0.1", port, API_KEY)
    try:
        yield client, fake_drip
    finally:
        await session.close()
        await runner.cleanup()
