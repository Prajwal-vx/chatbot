from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import AIProvider
from app.config import Settings
from app.conversation_service import (
    forget_all_data,
    forget_memories,
    get_context,
    list_memories,
    remember,
    save_inbound,
)
from app.intent import resolve_deterministic_intent
from app.language import control_language
from app.memory_policy import can_store_memory
from app.models import Conversation

_CONTROL_TEXT = {
    "stop": (
        "Paused. Send /start whenever you want me to reply again.",
        "जवाफ रोकिएको छ। फेरि सुरु गर्न /start पठाउनुहोस्।",
        "जवाब रोक दिए गए हैं। फिर शुरू करने के लिए /start भेजें।",
    ),
    "start": (
        "I’m active again. How can I help?",
        "म फेरि सक्रिय छु। कसरी मद्दत गरूँ?",
        "मैं फिर से सक्रिय हूँ। मैं आपकी क्या मदद करूँ?",
    ),
    "pause": (
        "Paused. Send /resume to continue.",
        "जवाफ रोकिएको छ। जारी राख्न /resume पठाउनुहोस्।",
        "जवाब रोक दिए गए हैं। जारी रखने के लिए /resume भेजें।",
    ),
    "forgot": (
        "I deleted the saved memories for this conversation.",
        "यो कुराकानीका लागि सुरक्षित गरिएका सम्झनाहरू मेटाएँ।",
        "इस बातचीत के लिए सेव की गई यादें हटा दी गई हैं।",
    ),
    "forgot_all": (
        "I deleted this conversation’s saved history and memories.",
        "यो कुराकानीको इतिहास र सुरक्षित सम्झनाहरू मेटाएँ।",
        "इस बातचीत का इतिहास और सेव की गई यादें हटा दी हैं।",
    ),
    "empty": (
        "I have no saved memories.",
        "मैले कुनै सम्झना सुरक्षित गरेको छैन।",
        "मेरे पास कोई सेव की गई यादें नहीं हैं।",
    ),
    "memory_title": ("Saved memories:", "सुरक्षित सम्झनाहरू:", "सेव की गई यादें:"),
    "remember_prompt": (
        "Tell me what you want saved after /remember.",
        "/remember पछि के सुरक्षित गर्ने हो लेख्नुहोस्।",
        "/remember के बाद बताएं कि क्या सेव करना है।",
    ),
    "remembered": (
        "I saved that preference. Send /memories to review it or /forget to delete it.",
        "त्यो प्राथमिकता सुरक्षित गरेँ। हेर्न /memories वा मेटाउन /forget पठाउनुहोस्।",
        "वह पसंद सेव कर ली। देखने के लिए /memories या हटाने के लिए /forget भेजें।",
    ),
    "sensitive": (
        "I can’t save passwords, codes, financial, health, or other sensitive information.",
        "म पासवर्ड, कोड, आर्थिक, स्वास्थ्य वा अन्य संवेदनशील जानकारी सुरक्षित गर्न सक्दिनँ।",
        "मैं पासवर्ड, कोड, वित्तीय, स्वास्थ्य या अन्य संवेदनशील जानकारी सेव नहीं कर सकता।",
    ),
    "handoff": (
        "I paused automated replies and recorded your request for a person. No live staff alert is configured yet.",
        "स्वचालित जवाफ रोकियो र मानव सहयोगको अनुरोध टिपोट गरियो। कर्मचारीलाई सूचना पठाउने व्यवस्था छैन।",
        "स्वचालित जवाब रोक दिए हैं और इंसानी मदद का अनुरोध दर्ज किया है। अभी स्टाफ को सूचना भेजने की व्यवस्था नहीं है।",
    ),
}


def control_reply(key: str, text: str, preferred_language: str) -> str:
    language = control_language(text)
    if text.startswith("/"):
        language = preferred_language
    if language in {"nepali", "nepali_latin"}:
        return _CONTROL_TEXT[key][1]
    if language in {"hindi", "hindi_latin"}:
        return _CONTROL_TEXT[key][2]
    return _CONTROL_TEXT[key][0]


async def generate_response(
    session: AsyncSession,
    settings: Settings,
    ai: AIProvider,
    sender: str,
    message_id: str,
    text: str,
) -> tuple[Conversation, str | None]:
    text = text[: settings.max_input_chars].strip()
    conversation, _ = await save_inbound(session, sender, message_id, text)
    already_replied = await session.scalar(
        select(Conversation.id).where(
            Conversation.id == conversation.id,
            Conversation.messages.any(message_id=f"reply:{message_id}"),
        )
    )
    if already_replied:
        return conversation, None

    command = text.casefold()
    response: str | None = None
    if command == "/stop":
        conversation.paused = True
        await session.commit()
        response = control_reply("stop", text, conversation.language)
    elif command in {"/start", "/resume"}:
        conversation.paused = False
        conversation.handoff_requested = False
        await session.commit()
        response = control_reply("start", text, conversation.language)
    elif command == "/pause":
        conversation.paused = True
        await session.commit()
        response = control_reply("pause", text, conversation.language)
    elif command in {"/forget", "/reset-memory"}:
        await forget_memories(session, conversation)
        response = control_reply("forgot", text, conversation.language)
    elif command == "/forget-all":
        response = control_reply("forgot_all", text, conversation.language)
        await forget_all_data(session, conversation)
    elif command == "/remember":
        response = control_reply("remember_prompt", text, conversation.language)
    elif command in {"/memories", "/memory"}:
        memories = await list_memories(session, conversation, settings.memory_limit)
        response = (
            control_reply("memory_title", text, conversation.language)
            + "\n"
            + "\n".join(f"• {value}" for value in memories)
            if memories
            else control_reply("empty", text, conversation.language)
        )
    elif command.startswith("/remember "):
        value = text[len("/remember ") :].strip()
        if len(value) > 500:
            response = "That memory is too long to save. Please keep it under 500 characters."
        elif not can_store_memory(value):
            response = control_reply("sensitive", text, conversation.language)
        else:
            await remember(session, conversation, value, settings.memory_limit)
            response = control_reply("remembered", text, conversation.language)
    elif command in {"/human", "/handoff"}:
        conversation.handoff_requested = True
        conversation.paused = True
        await session.commit()
        response = control_reply("handoff", text, conversation.language)

    if conversation.paused and response is None:
        return conversation, None
    if response is None:
        deterministic = resolve_deterministic_intent(text, settings.app_timezone)
        if deterministic is not None:
            response = deterministic
        else:
            history = await get_context(
                session,
                conversation,
                settings.conversation_history_limit,
                settings.max_context_chars,
            )
            memories = await list_memories(session, conversation, settings.memory_limit)
            response = await ai.reply(text, history=history, memories=memories)
    return conversation, response
