"""Constants for the Drip irrigation integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "drip"

DEFAULT_HOST: Final = "drip.local"
DEFAULT_PORT: Final = 80
DEFAULT_DURATION_MIN: Final = 10

ZONES: Final = ("herbs", "beds")
ZONE_HERBS: Final = "herbs"
ZONE_BEDS: Final = "beds"

RHYTHMS: Final = ("daily", "every_n_days", "weekdays")
WEEKDAYS: Final = ("sun", "mon", "tue", "wed", "thu", "fri", "sat")

MIN_DURATION_MIN: Final = 1
MAX_DURATION_MIN: Final = 45
MIN_N: Final = 1
MAX_N: Final = 30
MAX_SCHEDULES: Final = 16

SCAN_INTERVAL: Final = timedelta(seconds=15)
FAST_INTERVAL: Final = timedelta(seconds=5)
SCHEDULE_INTERVAL_S: Final = 60.0
WEATHER_INTERVAL_S: Final = 300.0

API_TIMEOUT_S: Final = 8.0
API_CONNECT_TIMEOUT_S: Final = 4.0
USER_AGENT: Final = "HomeAssistant-Drip/1.0"

ATTR_SCHEDULES: Final = "schedules"
ATTR_CAUSE: Final = "cause"
ATTR_REMAINING_S: Final = "remaining_s"
ATTR_DURATION_S: Final = "duration_s"

SERVICE_CREATE_SCHEDULE: Final = "create_schedule"
SERVICE_UPDATE_SCHEDULE: Final = "update_schedule"
SERVICE_DELETE_SCHEDULE: Final = "delete_schedule"
SERVICE_SET_SCHEDULE_ENABLED: Final = "set_schedule_enabled"
