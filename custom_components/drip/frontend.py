"""Register the bundled Lovelace card with Home Assistant."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.core import HomeAssistant

from .const import DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)

WWW_PATH = Path(__file__).parent / "www"
CARD_FILENAME = "drip-schedules-card.js"
DATA_FRONTEND = f"{DOMAIN}_frontend"


def card_url() -> str:
    """HA always serves /config/www as /local/."""
    return f"/local/drip/{CARD_FILENAME}?v={VERSION}"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Install the card under /local/drip and register it as a JS module.

    Custom element "does not exist" means the browser never ran the card JS.
    Serving via /drip/static + extra_js_url is unreliable on HA 2026 storage
    dashboards. Copying to config/www and loading /local/... is.
    """
    if hass.data.get(DATA_FRONTEND):
        return

    url = await hass.async_add_executor_job(_install_local_copy, hass)
    add_extra_js_url(hass, url)
    await _async_register_lovelace_resource(hass, url)
    hass.data[DATA_FRONTEND] = True
    _LOGGER.info("Drip Lovelace card available at %s", url)


def _install_local_copy(hass: HomeAssistant) -> str:
    dest_dir = Path(hass.config.path("www")) / "drip"
    dest_dir.mkdir(parents=True, exist_ok=True)
    src = WWW_PATH / CARD_FILENAME
    dest = dest_dir / CARD_FILENAME
    shutil.copyfile(src, dest)
    return card_url()


async def _async_register_lovelace_resource(hass: HomeAssistant, url: str) -> None:
    lovelace = hass.data.get("lovelace")
    resources = getattr(lovelace, "resources", None) if lovelace is not None else None
    try:
        from homeassistant.components.lovelace.resources import ResourceStorageCollection
    except ImportError:
        return
    if not isinstance(resources, ResourceStorageCollection):
        return

    # Load from disk first so create_item cannot wipe existing resources.
    await resources.async_get_info()
    existing = [
        item
        for item in resources.async_items()
        if CARD_FILENAME in str(item.get("url", ""))
    ]
    payload = {"res_type": "module", "url": url}
    if existing:
        if existing[0].get("url") != url:
            await resources.async_update_item(existing[0]["id"], payload)
        return
    await resources.async_create_item(payload)
