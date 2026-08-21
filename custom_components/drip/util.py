"""Helpers shared by the client and Home Assistant entities."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo("Europe/Berlin")


def parse_local(value: str | None) -> datetime | None:
    """Parse firmware local timestamps (Europe/Berlin, no offset)."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=BERLIN)
    except ValueError:
        return None
