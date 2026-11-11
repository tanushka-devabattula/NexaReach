import json
import os
import urllib.request
import urllib.error
import uuid
from .base import Channel


class MockWhatsAppChannel(Channel):
    def send(self, message: str, recipient: dict) -> dict:
        if not recipient.get("phone"):
            return {"success": False, "provider_message_id": None, "status": "failed", "error": "Recipient WhatsApp number missing"}
        return {"success": True, "provider_message_id": f"mock-whatsapp-{uuid.uuid4().hex[:8]}", "status": "sent", "error": None}


class MetaWhatsAppChannel(Channel):
    def send(self, message: str, recipient: dict) -> dict:
        try:
            token = os.getenv("WHATSAPP_ACCESS_TOKEN")
            phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
            version = os.getenv("WHATSAPP_API_VERSION")
            phone = recipient.get("phone")
            missing = [name for name, value in {
                "WHATSAPP_ACCESS_TOKEN": token,
                "WHATSAPP_PHONE_NUMBER_ID": phone_id,
                "WHATSAPP_API_VERSION": version,
                "recipient phone": phone
            }.items() if not value]
            if missing:
                raise ValueError("Missing WhatsApp configuration: " + ", ".join(missing))

            url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
            payload = {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "text",
                "text": {"preview_url": False, "body": message}
            }
            request = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(request, timeout=25) as response:
                data = json.loads(response.read().decode("utf-8"))
            message_id = (data.get("messages") or [{}])[0].get("id")
            return {"success": bool(message_id), "provider_message_id": message_id, "status": "sent" if message_id else "failed", "error": None if message_id else "Meta returned no message ID"}
        except Exception as exc:
            return {"success": False, "provider_message_id": None, "status": "failed", "error": str(exc)}
