"""Register the bundled Lovelace card with Home Assistant."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.core import HomeAssistant

from .const import DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)

WWW_PATH = Path(__file__).parent / "www"
STATIC_URL = f"/{DOMAIN}/static"
CARD_FILENAME = "drip-schedules-card.js"
DATA_FRONTEND = f"{DOMAIN}_frontend"


def card_url() -> str:
    """Versioned URL so browsers pick up card updates."""
    return f"{STATIC_URL}/{CARD_FILENAME}?v={VERSION}"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the card JS and register it as a Lovelace module resource.

    On HA 2026+, add_extra_js_url alone does not load custom cards on
    storage-mode dashboards. The element never defines and Lovelace shows
    "Configuration error". Persistent dashboard resources do.
    """
    if hass.data.get(DATA_FRONTEND):
        return
    hass.data[DATA_FRONTEND] = True

    await _async_register_static_path(hass)
    url = card_url()

    lovelace = hass.data.get("lovelace")
    resources = getattr(lovelace, "resources", None) if lovelace is not None else None

    try:
        from homeassistant.components.lovelace.resources import ResourceStorageCollection
    except ImportError:
        ResourceStorageCollection = None  # type: ignore[misc, assignment]

    if ResourceStorageCollection is not None and isinstance(
        resources, ResourceStorageCollection
    ):
        await resources.async_get_info()
        existing = [
            item
            for item in resources.async_items()
            if CARD_FILENAME in str(item.get("url", ""))
        ]
        if existing:
            current = existing[0]
            if current.get("url") != url:
                await resources.async_update_item(
                    current["id"], {"res_type": "module", "url": url}
                )
                _LOGGER.info("Updated drip Lovelace card resource to %s", url)
        else:
            await resources.async_create_item({"res_type": "module", "url": url})
            _LOGGER.info("Registered drip Lovelace card resource %s", url)
        return

    add_extra_js_url(hass, url)
    _LOGGER.debug("Registered drip card via extra JS URL %s", url)


async def _async_register_static_path(hass: HomeAssistant) -> None:
    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    url_path=STATIC_URL,
                    path=str(WWW_PATH),
                    cache_headers=False,
                )
            ]
        )
    except RuntimeError:
        _LOGGER.debug("Static path %s already registered", STATIC_URL)
    except (ImportError, AttributeError):
        hass.http.register_static_path(STATIC_URL, str(WWW_PATH), cache_headers=False)
