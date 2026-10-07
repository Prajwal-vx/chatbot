import hashlib

from redis.asyncio import Redis


async def allow_message(redis: Redis, sender: str, limit: int, window_seconds: int = 60) -> bool:
    digest = hashlib.sha256(sender.encode()).hexdigest()
    key = f"whatsapp:rate:{digest}"
    script = """
    local count = redis.call('INCR', KEYS[1])
    if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
    return count
    """
    count = int(await redis.eval(script, 1, key, window_seconds))
    return count <= limit
