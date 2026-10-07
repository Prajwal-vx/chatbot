from datetime import UTC, datetime, timedelta

CUSTOMER_SERVICE_WINDOW = timedelta(hours=24)


def can_send_freeform_reply(received_timestamp: int | None, now: datetime | None = None) -> bool:
    """Allow a free-form reply only inside the inbound message's service window."""
    if received_timestamp is None or received_timestamp <= 0:
        return False
    current = now or datetime.now(UTC)
    try:
        received = datetime.fromtimestamp(received_timestamp, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return False
    age = current - received
    return timedelta(0) <= age < CUSTOMER_SERVICE_WINDOW
