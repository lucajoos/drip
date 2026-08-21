"""HTTP client for the drip ESP8266 REST API."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import aiohttp

from .const import (
    API_CONNECT_TIMEOUT_S,
    API_TIMEOUT_S,
    MAX_DURATION_MIN,
    MAX_N,
    MIN_DURATION_MIN,
    MIN_N,
    RHYTHMS,
    USER_AGENT,
    WEEKDAYS,
    ZONES,
)

_LOGGER = logging.getLogger(__name__)

_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})(?::\d{2})?$")
_TIMEOUT = aiohttp.ClientTimeout(total=API_TIMEOUT_S, connect=API_CONNECT_TIMEOUT_S)


class DripError(Exception):
    """Base error talking to the controller."""


class DripAuthError(DripError):
    """API key rejected (HTTP 401)."""


class DripConflictError(DripError):
    """Zone busy / idle mismatch (HTTP 409)."""


class DripNotFoundError(DripError):
    """Resource missing (HTTP 404)."""


class DripApiError(DripError):
    """Non-success HTTP response from the controller."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def normalize_host(host: str) -> str:
    """Strip scheme and trailing slash from a user-supplied host."""
    value = host.strip()
    for prefix in ("http://", "https://"):
        if value.lower().startswith(prefix):
            value = value[len(prefix) :]
            break
    return value.split("/")[0].rstrip(".")


def normalize_time(value: str) -> str:
    """Normalize HA time selectors (`HH:MM:SS`) to firmware `HH:MM`."""
    match = _TIME_RE.match(value.strip())
    if not match:
        raise ValueError("time must be HH:MM")
    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour > 23 or minute > 59:
        raise ValueError("time must be HH:MM")
    return f"{hour:02d}:{minute:02d}"


def build_schedule_payload(
    *,
    zone: str,
    time: str,
    duration_min: int,
    rhythm: str = "daily",
    n: int | None = None,
    weekdays: list[str] | None = None,
    enabled: bool = True,
    rain_skip_enabled: bool = False,
    rain_skip_threshold_mm: float = 5.0,
) -> dict[str, Any]:
    """Build a POST/PUT body matching the firmware schedule schema."""
    if zone not in ZONES:
        raise ValueError("zone must be 'herbs' or 'beds'")
    if rhythm not in RHYTHMS:
        raise ValueError("rhythm must be daily, every_n_days or weekdays")
    duration = int(duration_min)
    if duration < MIN_DURATION_MIN or duration > MAX_DURATION_MIN:
        raise ValueError("duration_min must be 1..45")

    payload: dict[str, Any] = {
        "zone": zone,
        "time": normalize_time(time),
        "rhythm": rhythm,
        "durationMin": duration,
        "enabled": bool(enabled),
        "rainSkip": {
            "enabled": bool(rain_skip_enabled),
            "thresholdMm": float(rain_skip_threshold_mm),
        },
    }
    if payload["rainSkip"]["enabled"] and payload["rainSkip"]["thresholdMm"] <= 0:
        raise ValueError("rain_skip_threshold_mm must be > 0")

    if rhythm == "every_n_days":
        if n is None:
            raise ValueError("n is required for every_n_days")
        n_val = int(n)
        if n_val < MIN_N or n_val > MAX_N:
            raise ValueError("n must be 1..30")
        payload["n"] = n_val
    elif rhythm == "weekdays":
        days = list(weekdays or [])
        unknown = [d for d in days if d not in WEEKDAYS]
        if unknown:
            raise ValueError("weekdays must be from [sun,mon,tue,wed,thu,fri,sat]")
        if not days:
            raise ValueError("weekdays requires at least one day")
        payload["weekdays"] = days
    return payload


def schedule_to_payload(schedule: dict[str, Any], *, enabled: bool | None = None) -> dict[str, Any]:
    """Turn a GET /api/schedules item into a PUT body."""
    rain = schedule.get("rainSkip") or {}
    return build_schedule_payload(
        zone=schedule["zone"],
        time=schedule["time"],
        duration_min=int(schedule["durationMin"]),
        rhythm=schedule.get("rhythm", "daily"),
        n=schedule.get("n"),
        weekdays=schedule.get("weekdays"),
        enabled=schedule.get("enabled", True) if enabled is None else enabled,
        rain_skip_enabled=bool(rain.get("enabled", False)),
        rain_skip_threshold_mm=float(rain.get("thresholdMm", 5.0)),
    )


def _message_from_body(body: bytes) -> str:
    if not body:
        return "unknown error"
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return body.decode("utf-8", errors="replace")[:200]
    if isinstance(parsed, dict) and parsed.get("error"):
        return str(parsed["error"])
    return body.decode("utf-8", errors="replace")[:200]


class DripClient:
    """aiohttp client for drip's local REST API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        api_key: str,
    ) -> None:
        self._session = session
        self._host = normalize_host(host)
        self._port = int(port)
        self._api_key = api_key
        self.base_url = f"http://{self._host}:{self._port}"

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        expected: tuple[int, ...] = (200,),
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            async with self._session.request(
                method,
                url,
                json=json_body,
                headers=self._headers(),
                timeout=_TIMEOUT,
            ) as resp:
                body = await resp.read()
        except (TimeoutError, aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise DripError(f"controller unreachable: {err}") from err

        if resp.status == 401:
            raise DripAuthError("unauthorized")
        if resp.status == 409:
            raise DripConflictError(_message_from_body(body))
        if resp.status == 404:
            raise DripNotFoundError(_message_from_body(body))
        if resp.status not in expected:
            raise DripApiError(resp.status, _message_from_body(body))
        if resp.status == 204 or not body:
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError as err:
            raise DripError(f"invalid json: {err}") from err

    async def status(self) -> dict[str, Any]:
        """GET /api/status."""
        data = await self._request("GET", "/api/status")
        if not isinstance(data, dict):
            raise DripError("status response is not an object")
        return data

    async def weather(self) -> dict[str, Any]:
        """GET /api/weather."""
        data = await self._request("GET", "/api/weather")
        if not isinstance(data, dict):
            raise DripError("weather response is not an object")
        return data

    async def schedules(self) -> list[dict[str, Any]]:
        """GET /api/schedules."""
        data = await self._request("GET", "/api/schedules")
        if not isinstance(data, list):
            raise DripError("schedules response is not a list")
        return data

    async def create_schedule(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST /api/schedules."""
        data = await self._request(
            "POST", "/api/schedules", json_body=payload, expected=(201, 200)
        )
        if not isinstance(data, dict):
            raise DripError("create schedule response is not an object")
        return data

    async def update_schedule(self, schedule_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        """PUT /api/schedules/{id}."""
        data = await self._request(
            "PUT",
            f"/api/schedules/{int(schedule_id)}",
            json_body=payload,
            expected=(200,),
        )
        if not isinstance(data, dict):
            raise DripError("update schedule response is not an object")
        return data

    async def delete_schedule(self, schedule_id: int) -> None:
        """DELETE /api/schedules/{id}."""
        await self._request(
            "DELETE", f"/api/schedules/{int(schedule_id)}", expected=(204, 200)
        )

    async def water(self, zone: str, duration_min: int) -> dict[str, Any] | None:
        """POST /api/water. 409 (already watering) is treated as success."""
        try:
            data = await self._request(
                "POST",
                "/api/water",
                json_body={"zone": zone, "durationMin": int(duration_min)},
                expected=(200,),
            )
        except DripConflictError:
            _LOGGER.debug("zone %s already watering", zone)
            return None
        if data is not None and not isinstance(data, dict):
            raise DripError("water response is not an object")
        return data

    async def stop(self, zone: str) -> None:
        """POST /api/stop. 409 (not watering) is treated as success."""
        try:
            await self._request(
                "POST",
                "/api/stop",
                json_body={"zone": zone},
                expected=(204, 200),
            )
        except DripConflictError:
            _LOGGER.debug("zone %s already idle", zone)

    async def set_schedule_enabled(self, schedule_id: int, enabled: bool) -> dict[str, Any]:
        """GET the schedule, PUT it back with enabled flipped."""
        items = await self.schedules()
        found = next((item for item in items if item.get("id") == schedule_id), None)
        if found is None:
            raise DripNotFoundError("schedule nicht gefunden")
        payload = schedule_to_payload(found, enabled=enabled)
        return await self.update_schedule(schedule_id, payload)
