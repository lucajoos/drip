"""Sanity checks for the bundled Lovelace schedules card."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "custom_components" / "drip" / "www" / "drip-schedules-card.js"
FRONTEND = ROOT / "custom_components" / "drip" / "frontend.py"
MANIFEST = ROOT / "custom_components" / "drip" / "manifest.json"


def test_card_file_defines_element_and_services() -> None:
    text = CARD.read_text(encoding="utf-8")
    assert CARD.is_file()
    assert "drip-schedules-card" in text
    assert "customElements.define" in text
    assert "create_schedule" in text
    assert "update_schedule" in text
    assert "delete_schedule" in text
    assert "set_schedule_enabled" in text
    assert "window.customCards" in text


def test_frontend_registers_card_js() -> None:
    text = FRONTEND.read_text(encoding="utf-8")
    assert "add_extra_js_url" in text
    assert "drip-schedules-card.js" in text
    assert "async_register_static_paths" in text


def test_manifest_loads_frontend() -> None:
    import json

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert "frontend" in data.get("after_dependencies", [])
    assert data["version"]
