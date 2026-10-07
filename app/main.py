import json
import logging
import secrets
from contextlib import asynccontextmanager
from hmac import compare_digest

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import AIProvider
from app.config import get_settings
from app.conversation_engine import generate_response
from app.conversation_service import forget_memories, list_memories, save_reply
from app.database import SessionFactory, engine, get_session
from app.models import Conversation, WhatsAppNumber
from app.queue import enqueue_once
from app.rate_limit import allow_message
from app.whatsapp import parse_messages, verify_signature

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()
bearer = HTTPBearer(auto_error=False)


class DevMessage(BaseModel):
    sender: str = Field(min_length=8, max_length=32, pattern=r"^[0-9]+$")
    text: str = Field(min_length=1, max_length=12_000)


class ConversationState(BaseModel):
    paused: bool
    handoff_requested: bool = False


class WhatsAppNumberRequest(BaseModel):
    display_number: str = Field(min_length=7, max_length=24, pattern=r"^\+?[0-9]+$")
    phone_number_id: str = Field(min_length=5, max_length=64, pattern=r"^[0-9]+$")


WHATSAPP_SETUP_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>WhatsApp connection setup</title>
<style>
body{font:16px system-ui,sans-serif;background:#f4f7f5;color:#18251f;margin:0;padding:32px}
main{max-width:620px;margin:auto;background:white;padding:28px;border-radius:16px;box-shadow:0 8px 30px #13251b15}
h1{margin-top:0}p{line-height:1.5;color:#43534a}label{display:block;font-weight:600;margin:18px 0 6px}
input{box-sizing:border-box;width:100%;padding:12px;border:1px solid #bac8bf;border-radius:8px;font:inherit}
button{margin-top:18px;padding:11px 16px;border:0;border-radius:8px;background:#087b53;color:white;font:inherit;cursor:pointer}
#status{min-height:24px;margin-top:16px}small{color:#56655c}
</style></head><body><main>
<h1>Connect your WhatsApp Business number</h1>
<p>Enter the number connected to WhatsApp Cloud API and its Phone Number ID from Meta. These identify the number that should receive messages.</p>
<p><strong>Meta credentials:</strong> set the Cloud API access token, app secret, and webhook verification token in the server's <code>.env</code> file. This page never asks for or stores those secrets.</p>
<label for="admin-token">Admin API token</label><input id="admin-token" type="password" autocomplete="off" placeholder="ADMIN_API_TOKEN from .env">
<button id="load" type="button">Load saved number</button>
<form id="number-form">
<label for="display-number">WhatsApp Business phone number</label><input id="display-number" required minlength="7" maxlength="24" placeholder="+9779800000000">
<label for="phone-number-id">Meta Phone Number ID</label><input id="phone-number-id" required inputmode="numeric" pattern="[0-9]{5,64}" placeholder="Found in Meta WhatsApp API setup">
<button type="submit">Save WhatsApp number</button></form>
<div id="status" role="status" aria-live="polite"></div>
<small>After saving, send a message to this WhatsApp Business number. Meta must have the webhook URL configured and subscribed to the messages event.</small>
</main><script>
const token=()=>document.querySelector('#admin-token').value;
const status=(message)=>document.querySelector('#status').textContent=message;
async function api(method,body){const response=await fetch('/admin/settings/whatsapp',{method,headers:{'Authorization':'Bearer '+token(),'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const data=await response.json();if(!response.ok)throw new Error(data.detail||'Request failed');return data;}
document.querySelector('#load').onclick=async()=>{try{const data=await api('GET');document.querySelector('#display-number').value=data.display_number;document.querySelector('#phone-number-id').value=data.phone_number_id;status(data.configured?'Saved number loaded.':'No number saved yet.');}catch(error){status(error.message);}};
document.querySelector('#number-form').onsubmit=async(event)=>{event.preventDefault();try{const data=await api('PUT',{display_number:document.querySelector('#display-number').value,phone_number_id:document.querySelector('#phone-number-id').value});status('Saved '+data.display_number+'. Add the Cloud API credentials and webhook configuration to enable replies.');}catch(error){status(error.message);}};
</script></body></html>"""


async def require_admin(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    expected = settings.admin_api_token.get_secret_value()
    if not expected:
        raise HTTPException(status_code=503, detail="Admin API token is not configured")
    supplied = credentials.credentials if credentials else ""
    if not compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        try:
            async with SessionFactory() as session:
                configured_id = await session.scalar(
                    select(WhatsAppNumber.phone_number_id).where(WhatsAppNumber.id == 1)
                )
            if configured_id:
                await app.state.redis.set("whatsapp:configured_phone_number_id", configured_id)
        except Exception as exc:
            logger.warning("WhatsApp setup could not be loaded; error_type=%s", type(exc).__name__)
        yield
    finally:
        await app.state.redis.aclose()
        await engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.get("/admin/setup", response_class=HTMLResponse)
async def whatsapp_setup_page() -> HTMLResponse:
    return HTMLResponse(WHATSAPP_SETUP_PAGE)


@app.get("/health")
async def health(request: Request) -> dict[str, str]:
    redis: Redis = request.app.state.redis
    try:
        await redis.ping()
        redis_state = "ok"
    except Exception:
        redis_state = "unavailable"
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        database_state = "ok"
    except Exception:
        database_state = "unavailable"
    try:
        configured_id = await redis.get("whatsapp:configured_phone_number_id")
    except Exception:
        configured_id = None
    number_configured = bool(configured_id or settings.whatsapp_phone_number_id)
    ready = redis_state == database_state == "ok" and number_configured
    return {
        "status": "ok" if ready else "degraded",
        "redis": redis_state,
        "database": database_state,
        "whatsapp_number": "configured" if number_configured else "needs_setup",
    }


@app.get("/webhooks/whatsapp", response_class=PlainTextResponse)
async def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> PlainTextResponse:
    expected = settings.whatsapp_verify_token.get_secret_value()
    if hub_mode == "subscribe" and expected and hub_verify_token == expected and hub_challenge:
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Webhook verification failed")


@app.post("/webhooks/whatsapp")
async def receive_webhook(request: Request) -> dict[str, str]:
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > 1_000_000:
                raise HTTPException(status_code=413, detail="Webhook body too large")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid content length") from exc
    body = await request.body()
    if len(body) > 1_000_000:
        raise HTTPException(status_code=413, detail="Webhook body too large")
    app_secret = settings.whatsapp_app_secret.get_secret_value()
    if settings.app_env == "production" and not app_secret:
        raise HTTPException(
            status_code=503, detail="Webhook signature verification is not configured"
        )
    if app_secret and not verify_signature(
        body, request.headers.get("x-hub-signature-256"), app_secret
    ):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected a JSON object")
    messages = parse_messages(payload)
    redis: Redis = request.app.state.redis
    configured_phone_id = await redis.get("whatsapp:configured_phone_number_id")
    if not configured_phone_id:
        configured_phone_id = settings.whatsapp_phone_number_id
    for message in messages:
        if not await allow_message(redis, message.sender, settings.requests_per_minute):
            logger.warning("Inbound rate limit reached")
            continue
        if message.timestamp is None:
            logger.warning("Skipping message without a valid timestamp")
            continue
        if not message.phone_number_id or not configured_phone_id:
            logger.warning("Skipping message until a WhatsApp Business number is configured")
            continue
        if message.phone_number_id != configured_phone_id:
            logger.warning("Skipping event for an unconfigured WhatsApp Business number")
            continue
        await enqueue_once(
            redis,
            {
                "message_id": message.message_id,
                "sender": message.sender,
                "text": message.text[: settings.max_input_chars],
                "timestamp": message.timestamp,
                "phone_number_id": message.phone_number_id,
            },
        )
    logger.info("Accepted webhook with %d new text messages", len(messages))
    return {"status": "accepted"}


@app.get("/admin/settings/whatsapp", dependencies=[Depends(require_admin)])
async def get_whatsapp_number(
    session: AsyncSession = Depends(get_session),
) -> dict[str, str | bool]:
    number = await session.get(WhatsAppNumber, 1)
    if number is None:
        return {"configured": False, "display_number": "", "phone_number_id": ""}
    return {
        "configured": True,
        "display_number": number.display_number,
        "phone_number_id": number.phone_number_id,
    }


@app.put("/admin/settings/whatsapp", dependencies=[Depends(require_admin)])
async def save_whatsapp_number(
    payload: WhatsAppNumberRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str | bool]:
    number = await session.get(WhatsAppNumber, 1)
    if number is None:
        number = WhatsAppNumber(
            id=1,
            display_number=payload.display_number,
            phone_number_id=payload.phone_number_id,
        )
        session.add(number)
    else:
        number.display_number = payload.display_number
        number.phone_number_id = payload.phone_number_id
    await session.commit()
    await request.app.state.redis.set(
        "whatsapp:configured_phone_number_id", payload.phone_number_id
    )
    return {
        "configured": True,
        "display_number": number.display_number,
        "phone_number_id": number.phone_number_id,
    }


@app.get("/admin/conversations", dependencies=[Depends(require_admin)])
async def admin_conversations(
    session: AsyncSession = Depends(get_session)
) -> list[dict[str, object]]:
    rows = (
        await session.execute(
            select(Conversation).order_by(Conversation.updated_at.desc()).limit(200)
        )
    ).scalars()
    return [
        {
            "sender": row.sender,
            "paused": row.paused,
            "handoff_requested": row.handoff_requested,
            "updated_at": row.updated_at,
        }
        for row in rows
    ]


@app.get("/admin/conversations/{sender}/memories", dependencies=[Depends(require_admin)])
async def admin_memories(
    sender: str, session: AsyncSession = Depends(get_session)
) -> dict[str, object]:
    conversation = await session.scalar(select(Conversation).where(Conversation.sender == sender))
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"memories": await list_memories(session, conversation, settings.memory_limit)}


@app.delete("/admin/conversations/{sender}/memories", dependencies=[Depends(require_admin)])
async def admin_forget(sender: str, session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    conversation = await session.scalar(select(Conversation).where(Conversation.sender == sender))
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await forget_memories(session, conversation)
    return {"status": "deleted"}


@app.patch("/admin/conversations/{sender}", dependencies=[Depends(require_admin)])
async def admin_update_conversation(
    sender: str,
    state: ConversationState,
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    conversation = await session.scalar(select(Conversation).where(Conversation.sender == sender))
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conversation.paused = state.paused
    conversation.handoff_requested = state.handoff_requested
    await session.commit()
    return {"paused": conversation.paused, "handoff_requested": conversation.handoff_requested}


@app.delete("/admin/conversations/{sender}", dependencies=[Depends(require_admin)])
async def admin_delete_conversation(
    sender: str, session: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    conversation = await session.scalar(select(Conversation).where(Conversation.sender == sender))
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await session.delete(conversation)
    await session.commit()
    return {"status": "deleted"}


@app.post("/dev/messages", dependencies=[Depends(require_admin)])
async def simulate_message(
    payload: DevMessage,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    if not settings.enable_dev_simulator or settings.app_env != "development":
        raise HTTPException(status_code=404, detail="Simulator is disabled")
    if not settings.admin_api_token.get_secret_value():
        raise HTTPException(
            status_code=503, detail="Set ADMIN_API_TOKEN before using the simulator"
        )
    message_id = "sim:" + secrets.token_urlsafe(18)
    provider = AIProvider(settings)
    try:
        conversation, answer = await generate_response(
            session, settings, provider, payload.sender, message_id, payload.text
        )
        if answer is None:
            return {"reply": "Automated replies are paused for this conversation."}
        await save_reply(session, conversation, message_id, answer)
        return {"reply": answer}
    finally:
        await provider.client.close()
