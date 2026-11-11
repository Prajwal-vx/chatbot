import re

from app.tools.calculator import calculate

_TIME_INTENT = re.compile(r"\b(time is it|current time|what time|समय कति|कितने बजे)\b", re.IGNORECASE)
_CALC_INTENT = re.compile(r"[0-9][0-9.() +*/%\-]*[+*/%\-][0-9.() +*/%\-]*")


def resolve_deterministic_intent(text: str, timezone: str) -> str | None:
    lowered = text.casefold()
    if _TIME_INTENT.search(lowered):
        from app.tools.time import current_time

        return current_time(timezone)
    match = _CALC_INTENT.search(text)
    if match and len(match.group(0)) <= 100:
        try:
            result = calculate(match.group(0).strip())
        except (ValueError, ArithmeticError, SyntaxError):
            return None
        return str(result)
    return None
