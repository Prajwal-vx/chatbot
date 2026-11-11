import hashlib
import json
from collections.abc import Awaitable
from typing import Any, cast

from redis.asyncio import Redis

QUEUE_NAME = "whatsapp:incoming"
GROUP_NAME = "message-workers"
DEAD_LETTER_NAME = "whatsapp:dead-letter"
QUEUE_MAX_LENGTH = 100_000
DEAD_LETTER_MAX_LENGTH = 10_000


async def enqueue_once(redis: Redis, message: dict[str, Any], ttl_seconds: int = 86_400) -> bool:
    script = """
    if redis.call('SET', KEYS[1], '1', 'EX', ARGV[1], 'NX') then
      redis.call('XADD', KEYS[2], 'MAXLEN', '~', ARGV[3], '*', 'payload', ARGV[2], 'attempts', '0')
      return 1
    end
    return 0
    """
    result = cast(
        Awaitable[Any],
        redis.eval(
            script,
            2,
            f"whatsapp:seen:{message['message_id']}",
            QUEUE_NAME,
            str(ttl_seconds),
            json.dumps(message, ensure_ascii=False),
            str(QUEUE_MAX_LENGTH),
        ),
    )
    return await result == 1


async def ensure_group(redis: Redis) -> None:
    try:
        await redis.xgroup_create(QUEUE_NAME, GROUP_NAME, id="0", mkstream=True)
    except Exception as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def dequeue(redis: Redis, consumer: str) -> dict[str, Any] | None:
    await ensure_group(redis)
    # Reclaim abandoned deliveries before taking new work.
    claimed = await redis.xautoclaim(
        QUEUE_NAME, GROUP_NAME, consumer, min_idle_time=60_000, start_id="0-0", count=1
    )
    entries = claimed[1]
    if not entries:
        batches = await redis.xreadgroup(
            GROUP_NAME, consumer, {QUEUE_NAME: ">"}, count=1, block=5000
        )
        entries = batches[0][1] if batches else []
    if not entries:
        return None
    stream_id, fields = entries[0]
    payload = json.loads(fields["payload"])
    payload["_stream_id"] = stream_id
    payload["_attempts"] = int(fields.get("attempts", "0"))
    return payload


async def acknowledge(redis: Redis, message: dict[str, Any]) -> None:
    await redis.xack(QUEUE_NAME, GROUP_NAME, message["_stream_id"])


async def retry_or_dead_letter(
    redis: Redis, message: dict[str, Any], max_attempts: int = 3
) -> None:
    attempts = int(message.get("_attempts", 0)) + 1
    clean = {key: value for key, value in message.items() if not key.startswith("_")}
    destination = QUEUE_NAME if attempts < max_attempts else DEAD_LETTER_NAME
    if destination == DEAD_LETTER_NAME:
        sender_hash = hashlib.sha256(str(clean.get("sender", "")).encode()).hexdigest()
        clean = {"message_id": clean.get("message_id", ""), "sender_hash": sender_hash}
        max_length = DEAD_LETTER_MAX_LENGTH
    else:
        max_length = QUEUE_MAX_LENGTH
    await redis.xadd(
        destination,
        {"payload": json.dumps(clean, ensure_ascii=False), "attempts": str(attempts)},
        maxlen=max_length,
        approximate=True,
    )
    await acknowledge(redis, message)
