import httpx

from app.config import Settings


class WhatsAppClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = f"https://graph.facebook.com/{settings.whatsapp_api_version}"

    async def send_text(
        self, recipient: str, text: str, phone_number_id: str | None = None
    ) -> None:
        token = self.settings.whatsapp_access_token.get_secret_value()
        number_id = phone_number_id or self.settings.whatsapp_phone_number_id
        if not token or not number_id:
            raise RuntimeError("WhatsApp Cloud API credentials are not configured")
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.base_url}/{number_id}/messages",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": recipient,
                    "type": "text",
                    "text": {"preview_url": False, "body": text[:4000]},
                },
            )
            response.raise_for_status()
