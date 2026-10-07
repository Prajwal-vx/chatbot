from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def current_time(timezone: str) -> str:
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown timezone: {timezone}") from exc
    return datetime.now(zone).strftime("%A, %d %B %Y at %I:%M %p %Z")
