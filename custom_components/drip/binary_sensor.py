"""Binary sensor platform for Drip."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import DripCoordinator
from .entity import DripEntity

PARALLEL_UPDATES = 0

RTC_DESCRIPTION = BinarySensorEntityDescription(
    key="rtc",
    translation_key="rtc",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors."""
    coordinator: DripCoordinator = entry.runtime_data
    async_add_entities([DripRtcSensor(coordinator)])


class DripRtcSensor(DripEntity, BinarySensorEntity):
    """Whether the DS3231 RTC was detected."""

    entity_description = RTC_DESCRIPTION

    def __init__(self, coordinator: DripCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.uid}_rtc"

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        return bool(self.coordinator.data.status.get("rtcPresent"))
