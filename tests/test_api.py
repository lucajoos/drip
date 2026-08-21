"""Tests for the drip REST client against a fake ESP API."""

from __future__ import annotations

import pytest

from custom_components.drip.api import (
    DripApiError,
    DripAuthError,
    DripClient,
    DripNotFoundError,
    build_schedule_payload,
)


async def test_status_and_auth_header(drip_client) -> None:
    client, fake = drip_client
    status = await client.status()
    assert status["timeSource"] == "ntp"
    assert status["rtcPresent"] is True
    assert status["rssi"] == -61
    zones = {z["zone"]: z for z in status["zones"]}
    assert zones["herbs"]["active"] is False
    assert zones["beds"]["nextScheduledRun"] == "2026-07-26T05:00:00"


async def test_unauthorized(drip_client) -> None:
    client, _fake = drip_client
    bad = DripClient(client._session, "127.0.0.1", int(client.base_url.rsplit(":", 1)[1]), "wrong")
    with pytest.raises(DripAuthError):
        await bad.status()


async def test_water_and_stop(drip_client) -> None:
    client, fake = drip_client
    result = await client.water("herbs", 5)
    assert result == {"zone": "herbs", "durationS": 300}
    assert fake.zones["herbs"]["active"] is True
    assert fake.zones["herbs"]["remainingS"] == 300

    status = await client.status()
    herbs = next(z for z in status["zones"] if z["zone"] == "herbs")
    assert herbs["active"] is True
    assert herbs["cause"] == "manual"

    # 409 already watering is a no-op
    again = await client.water("herbs", 10)
    assert again is None
    assert fake.zones["herbs"]["durationS"] == 300

    await client.stop("herbs")
    assert fake.zones["herbs"]["active"] is False

    # 409 not watering is a no-op
    await client.stop("herbs")
    assert fake.zones["herbs"]["active"] is False


async def test_water_validation(drip_client) -> None:
    client, _fake = drip_client
    with pytest.raises(DripApiError) as err:
        await client.water("herbs", 0)
    assert err.value.status == 400


async def test_weather(drip_client) -> None:
    client, _fake = drip_client
    weather = await client.weather()
    assert weather["ok"] is True
    assert weather["past24Mm"] == 1.2
    assert weather["next12Mm"] == 0.4


async def test_schedule_crud(drip_client) -> None:
    client, fake = drip_client
    created = await client.create_schedule(
        build_schedule_payload(
            zone="herbs",
            time="05:00",
            duration_min=10,
            rain_skip_enabled=True,
            rain_skip_threshold_mm=5,
        )
    )
    assert created["id"] == 1
    assert created["zone"] == "herbs"
    assert created["time"] == "05:00"
    assert created["rhythm"] == "daily"
    assert created["durationMin"] == 10
    assert created["rainSkip"]["enabled"] is True

    listed = await client.schedules()
    assert len(listed) == 1

    updated = await client.update_schedule(
        1,
        build_schedule_payload(
            zone="beds",
            time="19:00",
            duration_min=20,
            rhythm="every_n_days",
            n=2,
            enabled=False,
        ),
    )
    assert updated["zone"] == "beds"
    assert updated["n"] == 2
    assert updated["enabled"] is False

    enabled = await client.set_schedule_enabled(1, True)
    assert enabled["enabled"] is True
    assert enabled["zone"] == "beds"
    assert enabled["n"] == 2

    await client.delete_schedule(1)
    assert await client.schedules() == []
    assert fake.schedules == []


async def test_schedule_not_found(drip_client) -> None:
    client, _fake = drip_client
    with pytest.raises(DripNotFoundError):
        await client.delete_schedule(99)
    with pytest.raises(DripNotFoundError):
        await client.set_schedule_enabled(99, True)


async def test_weekdays_schedule(drip_client) -> None:
    client, _fake = drip_client
    created = await client.create_schedule(
        build_schedule_payload(
            zone="beds",
            time="06:30:00",
            duration_min=15,
            rhythm="weekdays",
            weekdays=["mon", "wed", "fri"],
        )
    )
    assert created["time"] == "06:30"
    assert created["weekdays"] == ["mon", "wed", "fri"]


async def test_max_schedules(drip_client) -> None:
    client, fake = drip_client
    fake.next_id = 1
    payload = build_schedule_payload(zone="herbs", time="05:00", duration_min=5)
    for _ in range(16):
        await client.create_schedule(payload)
    with pytest.raises(DripApiError) as err:
        await client.create_schedule(payload)
    assert err.value.status == 507
