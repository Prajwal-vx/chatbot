import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis

from app.ai import AIProvider
from app.config import get_settings
from app.conversation_engine import generate_response
from app.conversation_service import delete_expired_conversations, get_conversation, save_reply
from app.database import SessionFactory
from app.language import control_language
from app.queue import acknowledge, dequeue, retry_or_dead_letter
from app.whatsapp_client import WhatsAppClient
from app.whatsapp_policy import can_send_freeform_reply

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def process_item(item: dict, ai: AIProvider, whatsapp: WhatsAppClient) -> None:
    if not can_send_freeform_reply(item.get("timestamp")):
        logger.info("Dropped stale or untimestamped message id=%s", item.get("message_id"))
        return
    async with SessionFactory() as session:
        conversation, response = await generate_response(
            session,
            get_settings(),
            ai,
            str(item["sender"]),
            str(item["message_id"]),
            str(item["text"]),
        )
        if response is None:
            return
        await whatsapp.send_text(str(item["sender"]), response, str(item["phone_number_id"]))
        await save_reply(session, conversation, str(item["message_id"]), response)


async def run() -> None:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    ai = AIProvider(settings)
    whatsapp = WhatsAppClient(settings)
    consumer = f"worker-{os.getpid()}"
    retention_task = asyncio.create_task(_retention_loop(settings.message_retention_days))
    try:
        while True:
            item = await dequeue(redis, consumer)
            if item is None:
                continue
            try:
                await process_item(item, ai, whatsapp)
                await acknowledge(redis, item)
            except Exception as exc:
                logger.error(
                    "Message processing failed; message id=%s error_type=%s",
                    item.get("message_id"),
                    type(exc).__name__,
                )
                if int(item.get("_attempts", 0)) >= 2:
                    try:
                        if not can_send_freeform_reply(item.get("timestamp")):
                            await acknowledge(redis, item)
                            continue
                        fallback = _fallback_reply(str(item.get("text", "")))
                        await whatsapp.send_text(
                            str(item["sender"]), fallback, str(item["phone_number_id"])
                        )
                        async with SessionFactory() as session:
                            conversation = await get_conversation(session, str(item["sender"]))
                            await save_reply(
                                session, conversation, str(item["message_id"]), fallback
                            )
                        await acknowledge(redis, item)
                        continue
                    except Exception as fallback_exc:
                        logger.error(
                            "Fallback delivery failed; error_type=%s", type(fallback_exc).__name__
                        )
                await asyncio.sleep(min(2 ** int(item.get("_attempts", 0)), 8))
                await retry_or_dead_letter(redis, item)
    finally:
        retention_task.cancel()
        try:
            await retention_task
        except asyncio.CancelledError:
            pass
        await ai.client.close()
        await redis.aclose()


async def _retention_loop(retention_days: int) -> None:
    while True:
        try:
            cutoff = datetime.now(UTC) - timedelta(days=retention_days)
            async with SessionFactory() as session:
                removed = await delete_expired_conversations(session, cutoff)
            if removed:
                logger.info("Removed %d expired conversations", removed)
        except Exception as exc:
            logger.error("Conversation retention cleanup failed; error_type=%s", type(exc).__name__)
        await asyncio.sleep(86_400)


def _fallback_reply(text: str) -> str:
    language = control_language(text)
    if language == "nepali":
        return "माफ गर्नुहोस्, अहिले जवाफ दिन समस्या भयो। कृपया केही बेरपछि फेरि प्रयास गर्नुहोस्।"
    if language == "nepali_latin":
        return "Maaf garnuhos, ahile jawaf dina samasya bhayo. Kripaya pachhi feri prayas garnuhos."
    if language == "hindi":
        return "माफ़ कीजिए, अभी जवाब देने में समस्या हो रही है। कृपया थोड़ी देर बाद फिर कोशिश करें।"
    if language == "hindi_latin":
        return "Maaf kijiye, abhi jawab dene mein dikkat hai. Kripya thodi der baad phir koshish karein."
    if language == "maithili_latin":
        return "Maaf karab, ekhan jawab deba me dikkat achhi. Kichhu der baad fer koshish karu."
    return "Sorry, I’m having trouble answering right now. Please try again shortly."


if __name__ == "__main__":
    asyncio.run(run())
