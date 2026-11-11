from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.language import control_language
from app.models import Conversation, Memory, Message


async def get_conversation(session: AsyncSession, sender: str) -> Conversation:
    statement = (
        insert(Conversation).values(sender=sender).on_conflict_do_nothing(index_elements=["sender"])
    )
    await session.execute(statement)
    await session.flush()
    result = await session.execute(select(Conversation).where(Conversation.sender == sender))
    conversation = result.scalar_one()
    return conversation


async def save_inbound(
    session: AsyncSession, sender: str, message_id: str, text: str
) -> tuple[Conversation, bool]:
    conversation = await get_conversation(session, sender)
    conversation.updated_at = datetime.now(UTC)
    if text and not text.startswith("/"):
        conversation.language = control_language(text)
    statement = (
        insert(Message)
        .values(message_id=message_id, conversation_id=conversation.id, role="user", content=text)
        .on_conflict_do_nothing(index_elements=["message_id"])
    )
    result = await session.execute(statement)
    await session.commit()
    return conversation, cast(CursorResult[Any], result).rowcount == 1


async def get_context(
    session: AsyncSession, conversation: Conversation, limit: int, max_chars: int = 16_000
) -> list[dict[str, str]]:
    query = (
        select(Message.role, Message.content)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(limit)
    )
    rows = list(reversed((await session.execute(query)).all()))
    selected: list[dict[str, str]] = []
    budget = max_chars
    for role, content in reversed(rows):
        content = content[:budget]
        if not content:
            break
        size = len(content)
        if size > budget:
            break
        selected.append({"role": role, "content": content})
        budget -= size
        if budget <= 0:
            break
    return list(reversed(selected))


async def save_reply(
    session: AsyncSession, conversation: Conversation, source_id: str, text: str
) -> None:
    session.add(
        Message(
            message_id=f"reply:{source_id}",
            conversation_id=conversation.id,
            role="assistant",
            content=text,
        )
    )
    await session.commit()


async def list_memories(session: AsyncSession, conversation: Conversation, limit: int) -> list[str]:
    query = (
        select(Memory.value)
        .where(Memory.conversation_id == conversation.id)
        .order_by(Memory.created_at.desc(), Memory.id.desc())
        .limit(limit)
    )
    return list((await session.execute(query)).scalars())


async def remember(
    session: AsyncSession, conversation: Conversation, value: str, limit: int
) -> None:
    session.add(Memory(conversation_id=conversation.id, value=value[:500]))
    await session.flush()
    old_ids = (
        (
            await session.execute(
                select(Memory.id)
                .where(Memory.conversation_id == conversation.id)
                .order_by(Memory.created_at.desc(), Memory.id.desc())
                .offset(limit)
            )
        )
        .scalars()
        .all()
    )
    if old_ids:
        await session.execute(delete(Memory).where(Memory.id.in_(old_ids)))
    await session.commit()


async def forget_memories(session: AsyncSession, conversation: Conversation) -> None:
    await session.execute(delete(Memory).where(Memory.conversation_id == conversation.id))
    await session.commit()


async def forget_all_data(session: AsyncSession, conversation: Conversation) -> None:
    await session.execute(delete(Message).where(Message.conversation_id == conversation.id))
    await session.execute(delete(Memory).where(Memory.conversation_id == conversation.id))
    conversation.language = "english"
    conversation.paused = False
    conversation.handoff_requested = False
    await session.commit()


async def delete_expired_conversations(session: AsyncSession, older_than: datetime) -> int:
    result = await session.execute(delete(Conversation).where(Conversation.updated_at < older_than))
    await session.commit()
    return int(cast(CursorResult[Any], result).rowcount or 0)
