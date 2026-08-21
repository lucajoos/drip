"""Schedule services for Drip."""

from __future__ import annotations

from typing import Any, cast

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .api import DripError, build_schedule_payload
from .const import (
    DOMAIN,
    MAX_DURATION_MIN,
    MAX_N,
    MIN_DURATION_MIN,
    MIN_N,
    RHYTHMS,
    SERVICE_CREATE_SCHEDULE,
    SERVICE_DELETE_SCHEDULE,
    SERVICE_SET_SCHEDULE_ENABLED,
    SERVICE_UPDATE_SCHEDULE,
    WEEKDAYS,
    ZONES,
)
from .coordinator import DripCoordinator

CONF_ENTRY_ID = "entry_id"
CONF_SCHEDULE_ID = "schedule_id"
CONF_ZONE = "zone"
CONF_TIME = "time"
CONF_RHYTHM = "rhythm"
CONF_N = "n"
CONF_WEEKDAYS = "weekdays"
CONF_DURATION_MIN = "duration_min"
CONF_ENABLED = "enabled"
CONF_RAIN_SKIP_ENABLED = "rain_skip_enabled"
CONF_RAIN_SKIP_THRESHOLD_MM = "rain_skip_threshold_mm"

SCHEDULE_FIELDS = {
    vol.Required(CONF_ZONE): vol.In(ZONES),
    vol.Required(CONF_TIME): cv.string,
    vol.Optional(CONF_RHYTHM, default="daily"): vol.In(RHYTHMS),
    vol.Optional(CONF_N): vol.All(vol.Coerce(int), vol.Range(min=MIN_N, max=MAX_N)),
    vol.Optional(CONF_WEEKDAYS): [vol.In(WEEKDAYS)],
    vol.Required(CONF_DURATION_MIN): vol.All(
        vol.Coerce(int), vol.Range(min=MIN_DURATION_MIN, max=MAX_DURATION_MIN)
    ),
    vol.Optional(CONF_ENABLED, default=True): cv.boolean,
    vol.Optional(CONF_RAIN_SKIP_ENABLED, default=False): cv.boolean,
    vol.Optional(CONF_RAIN_SKIP_THRESHOLD_MM, default=5.0): vol.All(
        vol.Coerce(float), vol.Range(min=0.1)
    ),
}

CREATE_SCHEMA = vol.Schema({**SCHEDULE_FIELDS, vol.Optional(CONF_ENTRY_ID): cv.string})
UPDATE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SCHEDULE_ID): vol.Coerce(int),
        **SCHEDULE_FIELDS,
        vol.Optional(CONF_ENTRY_ID): cv.string,
    }
)
DELETE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SCHEDULE_ID): vol.Coerce(int),
        vol.Optional(CONF_ENTRY_ID): cv.string,
    }
)
SET_ENABLED_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SCHEDULE_ID): vol.Coerce(int),
        vol.Required(CONF_ENABLED): cv.boolean,
        vol.Optional(CONF_ENTRY_ID): cv.string,
    }
)


def _payload_from_call(data: dict[str, Any]) -> dict[str, Any]:
    return build_schedule_payload(
        zone=data[CONF_ZONE],
        time=data[CONF_TIME],
        duration_min=data[CONF_DURATION_MIN],
        rhythm=data.get(CONF_RHYTHM, "daily"),
        n=data.get(CONF_N),
        weekdays=data.get(CONF_WEEKDAYS),
        enabled=data.get(CONF_ENABLED, True),
        rain_skip_enabled=data.get(CONF_RAIN_SKIP_ENABLED, False),
        rain_skip_threshold_mm=data.get(CONF_RAIN_SKIP_THRESHOLD_MM, 5.0),
    )


def _coordinator(hass: HomeAssistant, call: ServiceCall) -> DripCoordinator:
    entries = hass.config_entries.async_entries(DOMAIN)
    loaded = [e for e in entries if e.state is ConfigEntryState.LOADED]
    entry_id = call.data.get(CONF_ENTRY_ID)
    if entry_id:
        for entry in loaded:
            if entry.entry_id == entry_id:
                return cast(DripCoordinator, entry.runtime_data)
        raise HomeAssistantError(f"Unknown config entry: {entry_id}")
    if len(loaded) == 1:
        return cast(DripCoordinator, loaded[0].runtime_data)
    if not loaded:
        raise HomeAssistantError("Drip is not configured")
    raise HomeAssistantError("Multiple Drip devices: pass entry_id")


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register domain services once."""
    if hass.data.get(f"{DOMAIN}_services"):
        return
    hass.data[f"{DOMAIN}_services"] = True

    async def _refresh(coordinator: DripCoordinator) -> None:
        await coordinator.async_refresh_all()

    async def handle_create(call: ServiceCall) -> ServiceResponse | None:
        coordinator = _coordinator(hass, call)
        try:
            result = await coordinator.api.create_schedule(_payload_from_call(call.data))
        except (DripError, ValueError) as err:
            raise HomeAssistantError(str(err)) from err
        await _refresh(coordinator)
        if call.return_response:
            return {"schedule": result}
        return None

    async def handle_update(call: ServiceCall) -> ServiceResponse | None:
        coordinator = _coordinator(hass, call)
        try:
            result = await coordinator.api.update_schedule(
                call.data[CONF_SCHEDULE_ID], _payload_from_call(call.data)
            )
        except (DripError, ValueError) as err:
            raise HomeAssistantError(str(err)) from err
        await _refresh(coordinator)
        if call.return_response:
            return {"schedule": result}
        return None

    async def handle_delete(call: ServiceCall) -> ServiceResponse | None:
        coordinator = _coordinator(hass, call)
        try:
            await coordinator.api.delete_schedule(call.data[CONF_SCHEDULE_ID])
        except DripError as err:
            raise HomeAssistantError(str(err)) from err
        await _refresh(coordinator)
        return None

    async def handle_set_enabled(call: ServiceCall) -> ServiceResponse | None:
        coordinator = _coordinator(hass, call)
        try:
            result = await coordinator.api.set_schedule_enabled(
                call.data[CONF_SCHEDULE_ID], call.data[CONF_ENABLED]
            )
        except (DripError, ValueError) as err:
            raise HomeAssistantError(str(err)) from err
        await _refresh(coordinator)
        if call.return_response:
            return {"schedule": result}
        return None

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_SCHEDULE,
        handle_create,
        schema=CREATE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_SCHEDULE,
        handle_update,
        schema=UPDATE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_SCHEDULE,
        handle_delete,
        schema=DELETE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SCHEDULE_ENABLED,
        handle_set_enabled,
        schema=SET_ENABLED_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
