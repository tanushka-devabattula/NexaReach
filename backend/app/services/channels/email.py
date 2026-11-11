import os
import smtplib
import uuid
from email.message import EmailMessage
from .base import Channel


class MockEmailChannel(Channel):
    def send(self, message: str, recipient: dict) -> dict:
        if not recipient.get("email"):
            return {"success": False, "provider_message_id": None, "status": "failed", "error": "Recipient email missing"}
        return {"success": True, "provider_message_id": f"mock-email-{uuid.uuid4().hex[:8]}", "status": "sent", "error": None}


class SMTPEmailChannel(Channel):
    def send(self, message: str, recipient: dict) -> dict:
        try:
            email = recipient.get("email")
            required = ["SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "EMAIL_FROM"]
            missing = [key for key in required if not os.getenv(key)]
            if not email or missing:
                raise ValueError("Missing recipient email or SMTP configuration: " + ", ".join(missing))

            msg = EmailMessage()
            msg["Subject"] = os.getenv("EMAIL_SUBJECT", "NexaReach Notification")
            msg["From"] = os.environ["EMAIL_FROM"]
            msg["To"] = email
            msg.set_content(message)

            with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.getenv("SMTP_PORT", "587")), timeout=20) as server:
                server.starttls()
                server.login(os.environ["SMTP_USERNAME"], os.environ["SMTP_PASSWORD"])
                server.send_message(msg)

            return {"success": True, "provider_message_id": f"smtp-{uuid.uuid4().hex[:12]}", "status": "sent", "error": None}
        except Exception as exc:
            return {"success": False, "provider_message_id": None, "status": "failed", "error": str(exc)}
