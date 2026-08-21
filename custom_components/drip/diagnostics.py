"""Diagnostics for Drip (API key redacted)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from .coordinator import DripCoordinator

TO_REDACT = {CONF_API_KEY, "api_key", "X-API-Key"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: DripCoordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "status": data.status if data else None,
        "schedules": data.schedules if data else None,
        "weather": data.weather if data else None,
    }
