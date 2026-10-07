import re

_SENSITIVE = re.compile(
    r"\b(password|passcode|pin|one[- ]time password|otp|credit card|debit card|"
    r"bank account|social security|passport number|date of birth|home address|"
    r"medical|health|private key|api key|access token|secret key)\b",
    re.IGNORECASE,
)


def can_store_memory(value: str) -> bool:
    """Only allow explicit, bounded, non-sensitive user-approved memories."""
    return bool(value.strip()) and len(value) <= 500 and not _SENSITIVE.search(value)
