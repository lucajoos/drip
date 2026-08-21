"""Register the bundled Lovelace card with Home Assistant."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

WWW_PATH = Path(__file__).parent / "www"
STATIC_URL = f"/{DOMAIN}/static"
DATA_FRONTEND = f"{DOMAIN}_frontend"


def _card_version() -> str:
    manifest = Path(__file__).parent / "manifest.json"
    return json.loads(manifest.read_text(encoding="utf-8")).get("version", "0")


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve drip-schedules-card.js and load it on every Lovelace dashboard."""
    if hass.data.get(DATA_FRONTEND):
        return
    hass.data[DATA_FRONTEND] = True

    if hasattr(hass.http, "async_register_static_paths"):
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
    else:
        hass.http.register_static_path(STATIC_URL, str(WWW_PATH), cache_headers=False)

    js_url = f"{STATIC_URL}/drip-schedules-card.js?v={_card_version()}"
    from homeassistant.components.frontend import add_extra_js_url

    add_extra_js_url(hass, js_url)
    _LOGGER.debug("Registered drip Lovelace card at %s", js_url)
