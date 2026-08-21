"""Switch platform for Drip zones."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import DripError
from .const import ATTR_CAUSE, ATTR_DURATION_S, ATTR_REMAINING_S, ZONES
from .coordinator import DripCoordinator
from .entity import DripEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up zone switches."""
    coordinator: DripCoordinator = entry.runtime_data
    async_add_entities(DripZoneSwitch(coordinator, zone) for zone in ZONES)


class DripZoneSwitch(DripEntity, SwitchEntity):
    """On starts a timed watering; off stops the zone."""

    _attr_icon = "mdi:sprinkler-variant"

    def __init__(self, coordinator: DripCoordinator, zone: str) -> None:
        super().__init__(coordinator)
        self._zone = zone
        self._attr_unique_id = f"{coordinator.uid}_{zone}"
        self._attr_translation_key = zone

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.zone_status(self._zone).get("active"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        status = self.coordinator.zone_status(self._zone)
        if not status.get("active"):
            return {}
        attrs: dict[str, Any] = {}
        if "cause" in status:
            attrs[ATTR_CAUSE] = status["cause"]
        if "remainingS" in status:
            attrs[ATTR_REMAINING_S] = status["remainingS"]
        if "durationS" in status:
            attrs[ATTR_DURATION_S] = status["durationS"]
        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        duration = self.coordinator.manual_duration.get(self._zone, 10)
        try:
            await self.coordinator.api.water(self._zone, duration)
        except DripError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            await self.coordinator.api.stop(self._zone)
        except DripError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
