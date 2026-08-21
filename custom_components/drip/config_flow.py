"""Config flow for Drip."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_API_KEY, CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DripAuthError, DripClient, DripError, normalize_host
from .const import DEFAULT_HOST, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Required(CONF_API_KEY): str,
    }
)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Test connection and return normalized data."""
    host = normalize_host(data[CONF_HOST])
    port = int(data[CONF_PORT])
    api_key = str(data[CONF_API_KEY]).strip()
    if not host:
        raise CannotConnect
    if not api_key:
        raise InvalidAuth

    client = DripClient(async_get_clientsession(hass), host, port, api_key)
    try:
        await client.status()
    except DripAuthError as err:
        raise InvalidAuth from err
    except DripError as err:
        _LOGGER.debug("Drip connection failed: %s", err)
        raise CannotConnect from err

    return {
        CONF_HOST: host,
        CONF_PORT: port,
        CONF_API_KEY: api_key,
    }


class DripConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Drip."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception during drip setup")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(f"{info[CONF_HOST]}:{info[CONF_PORT]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Drip", data=info)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
