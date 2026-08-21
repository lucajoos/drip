"""Number platform for manual watering duration."""

from __future__ import annotations

from homeassistant.components.number import NumberMode, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEFAULT_DURATION_MIN, MAX_DURATION_MIN, MIN_DURATION_MIN, ZONES
from .coordinator import DripCoordinator
from .entity import DripEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up duration number entities."""
    coordinator: DripCoordinator = entry.runtime_data
    async_add_entities(DripDurationNumber(coordinator, zone) for zone in ZONES)


class DripDurationNumber(DripEntity, RestoreNumber):
    """HA-side duration used when turning a zone switch on."""

    _attr_icon = "mdi:timer-outline"
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = MIN_DURATION_MIN
    _attr_native_max_value = MAX_DURATION_MIN
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, coordinator: DripCoordinator, zone: str) -> None:
        super().__init__(coordinator)
        self._zone = zone
        self._attr_unique_id = f"{coordinator.uid}_{zone}_duration"
        self._attr_translation_key = f"{zone}_duration"

    @property
    def native_value(self) -> float:
        return float(self.coordinator.manual_duration.get(self._zone, DEFAULT_DURATION_MIN))

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.manual_duration[self._zone] = int(value)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            self.coordinator.manual_duration[self._zone] = int(last.native_value)
