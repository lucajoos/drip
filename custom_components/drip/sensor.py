"""Sensor platform for Drip."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfInformation,
    UnitOfPrecipitationDepth,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import ATTR_SCHEDULES, ZONES
from .coordinator import DripCoordinator
from .entity import DripEntity
from .util import parse_local

PARALLEL_UPDATES = 0


def _zone(coordinator: DripCoordinator, zone: str) -> dict[str, Any]:
    return coordinator.zone_status(zone)


@dataclass(frozen=True, kw_only=True)
class DripSensorDescription(SensorEntityDescription):
    """Sensor with a value extractor."""

    value_fn: Callable[[DripCoordinator], StateType | datetime]
    attrs_fn: Callable[[DripCoordinator], dict[str, Any]] | None = None


def _zone_descriptions(zone: str) -> tuple[DripSensorDescription, ...]:
    return (
        DripSensorDescription(
            key=f"{zone}_remaining",
            translation_key=f"{zone}_remaining",
            device_class=SensorDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.SECONDS,
            state_class=SensorStateClass.MEASUREMENT,
            icon="mdi:timer-sand",
            value_fn=lambda c, z=zone: _zone(c, z).get("remainingS")
            if _zone(c, z).get("active")
            else None,
        ),
        DripSensorDescription(
            key=f"{zone}_next_run",
            translation_key=f"{zone}_next_run",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:calendar-clock",
            value_fn=lambda c, z=zone: parse_local(_zone(c, z).get("nextScheduledRun")),
        ),
        DripSensorDescription(
            key=f"{zone}_last_run",
            translation_key=f"{zone}_last_run",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:calendar-end",
            value_fn=lambda c, z=zone: parse_local(_zone(c, z).get("lastRunEnd")),
        ),
        DripSensorDescription(
            key=f"{zone}_last_duration",
            translation_key=f"{zone}_last_duration",
            device_class=SensorDeviceClass.DURATION,
            native_unit_of_measurement=UnitOfTime.SECONDS,
            icon="mdi:timer",
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=lambda c, z=zone: _zone(c, z).get("lastRunDurationS"),
        ),
        DripSensorDescription(
            key=f"{zone}_cause",
            translation_key=f"{zone}_cause",
            icon="mdi:information-outline",
            entity_category=EntityCategory.DIAGNOSTIC,
            value_fn=lambda c, z=zone: _zone(c, z).get("cause")
            if _zone(c, z).get("active")
            else None,
        ),
    )


SENSORS: tuple[DripSensorDescription, ...] = (
    *(_desc for zone in ZONES for _desc in _zone_descriptions(zone)),
    DripSensorDescription(
        key="rssi",
        translation_key="rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda c: c.data.status.get("rssi") if c.data else None,
    ),
    DripSensorDescription(
        key="uptime",
        translation_key="uptime",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:clock-outline",
        value_fn=lambda c: c.data.status.get("uptimeS") if c.data else None,
    ),
    DripSensorDescription(
        key="free_heap",
        translation_key="free_heap",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda c: c.data.status.get("freeHeap") if c.data else None,
    ),
    DripSensorDescription(
        key="time_source",
        translation_key="time_source",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:clock-check-outline",
        value_fn=lambda c: c.data.status.get("timeSource") if c.data else None,
    ),
    DripSensorDescription(
        key="schedules",
        translation_key="schedules",
        icon="mdi:calendar-month",
        value_fn=lambda c: len(c.data.schedules) if c.data else 0,
        attrs_fn=lambda c: {ATTR_SCHEDULES: c.data.schedules if c.data else []},
    ),
    DripSensorDescription(
        key="precip_past_24h",
        translation_key="precip_past_24h",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-rainy",
        suggested_display_precision=1,
        value_fn=lambda c: (c.data.weather.get("past24Mm") if c.data else None)
        if c.data and c.data.weather.get("ok")
        else None,
    ),
    DripSensorDescription(
        key="precip_next_12h",
        translation_key="precip_next_12h",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-pouring",
        suggested_display_precision=1,
        value_fn=lambda c: (c.data.weather.get("next12Mm") if c.data else None)
        if c.data and c.data.weather.get("ok")
        else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator: DripCoordinator = entry.runtime_data
    async_add_entities(DripSensor(coordinator, description) for description in SENSORS)


class DripSensor(DripEntity, SensorEntity):
    """Sensor backed by coordinator data."""

    entity_description: DripSensorDescription

    def __init__(
        self, coordinator: DripCoordinator, description: DripSensorDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.uid}_{description.key}"

    @property
    def native_value(self) -> StateType | datetime:
        return self.entity_description.value_fn(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator)
