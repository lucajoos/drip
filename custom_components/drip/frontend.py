"""Register the bundled Lovelace card with Home Assistant."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.core import HomeAssistant
from homeassistant.helpers.start import async_at_started

from .const import DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)

WWW_PATH = Path(__file__).parent / "www"
CARD_FILENAME = "drip-schedules-card.js"
DATA_FRONTEND = f"{DOMAIN}_frontend"
RESOURCE_URL = f"/local/drip/{CARD_FILENAME}"


def card_url() -> str:
    """HA always serves /config/www as /local/."""
    return f"{RESOURCE_URL}?v={VERSION}"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Copy the card to /local/drip and register it after HA has started.

    Opening /local/drip/drip-schedules-card.js in a tab only downloads the
    file. Lovelace will not run it unless it is a dashboard resource (or
    extra JS). On HA 2026 storage dashboards extra_js_url is not enough.
    """
    if hass.data.get(DATA_FRONTEND):
        return
    hass.data[DATA_FRONTEND] = True

    await hass.async_add_executor_job(_install_local_copy, hass)

    async def _when_started(_hass: HomeAssistant) -> None:
        await _async_finish_registration(_hass)

    async_at_started(hass, _when_started)


def _install_local_copy(hass: HomeAssistant) -> None:
    dest_dir = Path(hass.config.path("www")) / "drip"
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(WWW_PATH / CARD_FILENAME, dest_dir / CARD_FILENAME)
    _LOGGER.info("Copied drip Lovelace card to %s", dest_dir / CARD_FILENAME)


async def _async_finish_registration(hass: HomeAssistant) -> None:
    url = card_url()
    try:
        add_extra_js_url(hass, url)
        add_extra_js_url(hass, url, es5=True)
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Could not add extra JS URL")

    registered = await _async_register_lovelace_resource(hass, url)
    if registered:
        _LOGGER.info("Drip Lovelace card registered as resource %s", url)
        return

    _LOGGER.warning(
        "Could not auto-register the drip Lovelace card. Add a dashboard "
        "resource: URL %s, type JavaScript module. Then hard-reload the browser.",
        RESOURCE_URL,
    )
    try:
        from homeassistant.components.persistent_notification import async_create

        async_create(
            hass,
            "Die Gießpläne-Karte wird vom Dashboard nicht geladen. "
            "Einstellungen → Dashboards → Ressourcen → Hinzufügen:\n"
            f"URL: `{RESOURCE_URL}`\n"
            "Typ: JavaScript-Modul\n"
            "Danach den Browser hart neu laden. "
            "YAML-Typ: `custom:drip-schedules-card`.",
            title="Drip: Lovelace-Karte einbinden",
            notification_id="drip_lovelace_card",
        )
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Could not create persistent notification")


async def _async_register_lovelace_resource(hass: HomeAssistant, url: str) -> bool:
    lovelace = hass.data.get("lovelace")
    resources = getattr(lovelace, "resources", None) if lovelace is not None else None
    try:
        from homeassistant.components.lovelace.resources import ResourceStorageCollection
    except ImportError:
        _LOGGER.debug("ResourceStorageCollection not available")
        return False
    if not isinstance(resources, ResourceStorageCollection):
        _LOGGER.debug("Lovelace resources are %s", type(resources))
        return False

    try:
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
            return True
        await resources.async_create_item(payload)
        return True
    except Exception:
        _LOGGER.exception("Failed to create Lovelace resource for drip card")
        return False
