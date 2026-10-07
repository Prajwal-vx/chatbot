import hashlib
import hmac
import unittest

from app.intent import resolve_deterministic_intent
from app.language import detect_language
from app.memory_policy import can_store_memory
from app.tools.calculator import calculate
from app.whatsapp import IncomingMessage, parse_messages, verify_signature
from app.whatsapp_policy import can_send_freeform_reply


class WhatsAppUnitTests(unittest.TestCase):
    def test_webhook_signature_accepts_exact_body(self) -> None:
        secret = "local-test-secret"
        body = b'{"object":"whatsapp_business_account"}'
        signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        self.assertTrue(verify_signature(body, signature, secret))
        self.assertFalse(verify_signature(body + b" ", signature, secret))
        self.assertFalse(verify_signature(body, None, secret))

    def test_parse_messages_ignores_status_and_non_text_events(self) -> None:
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": "wamid.1",
                                        "from": "9779800000000",
                                        "type": "text",
                                        "text": {"body": "Namaste"},
                                    },
                                    {"id": "wamid.2", "from": "9779800000000", "type": "image"},
                                    {
                                        "id": "wamid.3",
                                        "from": "not-a-number",
                                        "type": "text",
                                        "text": {"body": "ignore"},
                                    },
                                ],
                                "statuses": [{"id": "wamid.outbound"}],
                                "metadata": {"phone_number_id": "123456789"},
                            }
                        }
                    ]
                }
            ]
        }

        self.assertEqual(
            parse_messages(payload),
            [
                IncomingMessage(
                    message_id="wamid.1",
                    sender="9779800000000",
                    text="Namaste",
                    phone_number_id="123456789",
                )
            ],
        )
        self.assertEqual(parse_messages({"entry": None}), [])

    def test_memory_requires_explicit_safe_bounded_content(self) -> None:
        self.assertTrue(can_store_memory("Prefers replies in Nepali"))
        self.assertFalse(can_store_memory("My password is hunter2"))
        self.assertFalse(can_store_memory(" "))
        self.assertFalse(can_store_memory("x" * 501))

    def test_calculator_rejects_code_and_applies_bounds(self) -> None:
        self.assertEqual(calculate("(12 + 3) * 2"), 30)
        with self.assertRaises((ValueError, SyntaxError)):
            calculate("__import__('os').system('whoami')")

    def test_deterministic_calculator_intent(self) -> None:
        self.assertEqual(resolve_deterministic_intent("What is 12 * 4?", "Asia/Kathmandu"), "48")

    def test_language_detection_for_script_and_code_switching(self) -> None:
        self.assertIn("Romanized Nepali", detect_language("timi k xa"))
        self.assertIn("code-switch", detect_language("नमस्ते hello"))

    def test_freeform_reply_window_rejects_missing_expired_and_future_timestamps(self) -> None:
        from datetime import UTC, datetime

        now = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
        recent = int(now.timestamp()) - 60
        expired = int(now.timestamp()) - 86_401
        future = int(now.timestamp()) + 120
        self.assertTrue(can_send_freeform_reply(recent, now))
        self.assertFalse(can_send_freeform_reply(expired, now))
        self.assertFalse(can_send_freeform_reply(future, now))
        self.assertFalse(can_send_freeform_reply(None, now))


if __name__ == "__main__":
    unittest.main()
