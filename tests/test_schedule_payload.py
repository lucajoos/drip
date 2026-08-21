"""Validation of schedule payloads (firmware rules, HA snake_case)."""

from __future__ import annotations

import pytest

from custom_components.drip.api import (
    build_schedule_payload,
    normalize_host,
    normalize_time,
    schedule_to_payload,
)
from custom_components.drip.util import parse_local


def test_normalize_host_strips_scheme() -> None:
    assert normalize_host("http://drip.local/") == "drip.local"
    assert normalize_host("https://192.168.1.20") == "192.168.1.20"
    assert normalize_host(" drip.local. ") == "drip.local"


def test_normalize_time_from_ha_selector() -> None:
    assert normalize_time("5:00") == "05:00"
    assert normalize_time("05:00:00") == "05:00"
    with pytest.raises(ValueError):
        normalize_time("25:00")
    with pytest.raises(ValueError):
        normalize_time("noon")


def test_daily_payload() -> None:
    payload = build_schedule_payload(
        zone="herbs",
        time="05:00",
        duration_min=10,
        rain_skip_enabled=True,
        rain_skip_threshold_mm=5,
    )
    assert payload == {
        "zone": "herbs",
        "time": "05:00",
        "rhythm": "daily",
        "durationMin": 10,
        "enabled": True,
        "rainSkip": {"enabled": True, "thresholdMm": 5.0},
    }


def test_every_n_days_requires_n() -> None:
    with pytest.raises(ValueError, match="n is required"):
        build_schedule_payload(
            zone="beds", time="19:00", duration_min=20, rhythm="every_n_days"
        )
    payload = build_schedule_payload(
        zone="beds", time="19:00", duration_min=20, rhythm="every_n_days", n=2
    )
    assert payload["n"] == 2
    assert "weekdays" not in payload


def test_weekdays_requires_days() -> None:
    with pytest.raises(ValueError, match="at least one day"):
        build_schedule_payload(
            zone="beds", time="06:30", duration_min=15, rhythm="weekdays"
        )
    with pytest.raises(ValueError, match="weekdays must be"):
        build_schedule_payload(
            zone="beds",
            time="06:30",
            duration_min=15,
            rhythm="weekdays",
            weekdays=["montag"],
        )


def test_duration_and_zone_limits() -> None:
    with pytest.raises(ValueError, match="zone"):
        build_schedule_payload(zone="lawn", time="05:00", duration_min=10)
    with pytest.raises(ValueError, match="duration_min"):
        build_schedule_payload(zone="herbs", time="05:00", duration_min=46)
    with pytest.raises(ValueError, match="duration_min"):
        build_schedule_payload(zone="herbs", time="05:00", duration_min=0)


def test_schedule_to_payload_roundtrip() -> None:
    schedule = {
        "id": 3,
        "zone": "beds",
        "time": "06:30",
        "rhythm": "weekdays",
        "weekdays": ["mon", "fri"],
        "durationMin": 15,
        "enabled": True,
        "rainSkip": {"enabled": True, "thresholdMm": 3.5},
        "nextRun": "2026-07-27T06:30:00",
    }
    payload = schedule_to_payload(schedule, enabled=False)
    assert payload["enabled"] is False
    assert payload["weekdays"] == ["mon", "fri"]
    assert payload["rainSkip"]["thresholdMm"] == 3.5
    assert "id" not in payload
    assert "nextRun" not in payload


def test_parse_local_berlin() -> None:
    dt = parse_local("2026-07-25T14:30:00")
    assert dt is not None
    assert dt.year == 2026
    assert dt.hour == 14
    assert dt.tzinfo is not None
    assert dt.tzinfo.key == "Europe/Berlin"
    assert parse_local(None) is None
    assert parse_local("nope") is None
