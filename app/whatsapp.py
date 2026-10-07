import hashlib
import hmac
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IncomingMessage:
    message_id: str
    sender: str
    text: str
    timestamp: int | None = None
    phone_number_id: str | None = None


def verify_signature(body: bytes, signature: str | None, app_secret: str) -> bool:
    if not signature or not signature.startswith("sha256=") or not app_secret:
        return False
    expected = "sha256=" + hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_messages(payload: dict[str, Any]) -> list[IncomingMessage]:
    messages: list[IncomingMessage] = []
    entries = payload.get("entry", [])
    if not isinstance(entries, list):
        return messages
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("changes", []), list):
            continue
        for change in entry.get("changes", []):
            if not isinstance(change, dict):
                continue
            value = change.get("value", {})
            if not isinstance(value, dict) or not isinstance(value.get("messages", []), list):
                continue
            for message in value.get("messages", []):
                if not isinstance(message, dict) or message.get("type") != "text":
                    continue
                text_data = message.get("text", {})
                text = text_data.get("body", "") if isinstance(text_data, dict) else ""
                message_id = message.get("id")
                sender = message.get("from")
                raw_timestamp = message.get("timestamp")
                metadata = value.get("metadata", {})
                phone_number_id = (
                    metadata.get("phone_number_id") if isinstance(metadata, dict) else None
                )
                timestamp = (
                    int(raw_timestamp)
                    if isinstance(raw_timestamp, str) and raw_timestamp.isdigit()
                    else None
                )
                if (
                    isinstance(text, str)
                    and isinstance(message_id, str)
                    and isinstance(sender, str)
                ):
                    text = text.strip()
                    if text and sender.isdigit():
                        messages.append(
                            IncomingMessage(
                                message_id,
                                sender,
                                text,
                                timestamp,
                                str(phone_number_id) if phone_number_id else None,
                            )
                        )
    return messages
