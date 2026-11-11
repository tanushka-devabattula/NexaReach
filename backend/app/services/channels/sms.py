import os
import uuid
from .base import Channel


class MockSMSChannel(Channel):
    def send(self, message: str, recipient: dict) -> dict:
        if not recipient.get("phone"):
            return {"success": False, "provider_message_id": None, "status": "failed", "error": "Recipient phone missing"}
        return {"success": True, "provider_message_id": f"mock-sms-{uuid.uuid4().hex[:8]}", "status": "sent", "error": None}


class TwilioSMSChannel(Channel):
    def send(self, message: str, recipient: dict) -> dict:
        try:
            from twilio.rest import Client
            phone = recipient.get("phone")
            required = ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_PHONE_NUMBER"]
            missing = [key for key in required if not os.getenv(key)]
            if not phone or missing:
                raise ValueError("Missing recipient phone or Twilio configuration: " + ", ".join(missing))
            result = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"]).messages.create(
                body=message, from_=os.environ["TWILIO_PHONE_NUMBER"], to=phone
            )
            return {"success": True, "provider_message_id": result.sid, "status": "sent", "error": None}
        except Exception as exc:
            return {"success": False, "provider_message_id": None, "status": "failed", "error": str(exc)}
