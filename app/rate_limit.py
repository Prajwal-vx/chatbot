import hashlib
from collections.abc import Awaitable
from typing import Any, cast

from redis.asyncio import Redis


async def allow_message(redis: Redis, sender: str, limit: int, window_seconds: int = 60) -> bool:
    digest = hashlib.sha256(sender.encode()).hexdigest()
    key = f"whatsapp:rate:{digest}"
    script = """
    local count = redis.call('INCR', KEYS[1])
    if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
    return count
    """
    result = cast(Awaitable[Any], redis.eval(script, 1, key, str(window_seconds)))
    count = int(await result)
    return count <= limit
