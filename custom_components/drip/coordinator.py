"""DataUpdateCoordinator for drip."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DripAuthError, DripClient, DripError
from .const import (
    DEFAULT_DURATION_MIN,
    DOMAIN,
    FAST_INTERVAL,
    SCAN_INTERVAL,
    SCHEDULE_INTERVAL_S,
    WEATHER_INTERVAL_S,
    ZONES,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class DripData:
    """Snapshot of controller state."""

    status: dict[str, Any]
    schedules: list[dict[str, Any]]
    weather: dict[str, Any]


class DripCoordinator(DataUpdateCoordinator[DripData]):
    """Poll status often; schedules and weather less frequently."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.entry = entry
        self.api = DripClient(
            async_get_clientsession(hass),
            entry.data[CONF_HOST],
            entry.data[CONF_PORT],
            entry.data[CONF_API_KEY],
        )
        self.manual_duration: dict[str, int] = {zone: DEFAULT_DURATION_MIN for zone in ZONES}
        self._schedules: list[dict[str, Any]] | None = None
        self._weather: dict[str, Any] | None = None
        self._last_schedules = 0.0
        self._last_weather = 0.0
        self._force_full = True

    @property
    def uid(self) -> str:
        """Stable id prefix for entities."""
        return self.entry.unique_id or self.entry.entry_id

    @property
    def device_info(self) -> DeviceInfo:
        """Single device for all drip entities."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.uid)},
            name="Drip",
            manufacturer="drip",
            model="NodeMCU V3 (ESP8266)",
            configuration_url=self.api.base_url,
        )

    def zone_status(self, zone: str) -> dict[str, Any]:
        """Return the status object for a zone, or empty dict."""
        if not self.data:
            return {}
        for item in self.data.status.get("zones", []):
            if item.get("zone") == zone:
                return item
        return {}

    def request_full_refresh(self) -> None:
        """Fetch schedules and weather on the next poll."""
        self._force_full = True

    async def async_refresh_all(self) -> None:
        """Immediately refresh status, schedules, and weather."""
        self.request_full_refresh()
        await self.async_request_refresh()

    async def _async_update_data(self) -> DripData:
        try:
            status = await self.api.status()
        except DripAuthError as err:
            raise UpdateFailed("invalid API key") from err
        except DripError as err:
            raise UpdateFailed(str(err)) from err

        now = time.monotonic()
        force = self._force_full
        self._force_full = False

        if force or self._schedules is None or now - self._last_schedules >= SCHEDULE_INTERVAL_S:
            try:
                self._schedules = await self.api.schedules()
                self._last_schedules = now
            except DripError as err:
                if self._schedules is None:
                    raise UpdateFailed(str(err)) from err
                _LOGGER.warning("Could not refresh schedules: %s", err)

        if force or self._weather is None or now - self._last_weather >= WEATHER_INTERVAL_S:
            try:
                self._weather = await self.api.weather()
                self._last_weather = now
            except DripError as err:
                if self._weather is None:
                    self._weather = {}
                _LOGGER.warning("Could not refresh weather: %s", err)

        watering = any(zone.get("active") for zone in status.get("zones", []))
        self.update_interval = FAST_INTERVAL if watering else SCAN_INTERVAL

        return DripData(
            status=status,
            schedules=self._schedules or [],
            weather=self._weather or {},
        )
