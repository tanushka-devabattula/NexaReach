import os
import uuid
from .base import Channel


class MockPushChannel(Channel):
    def send(self, message: str, recipient: dict) -> dict:
        if not recipient.get("device_token"):
            return {"success": False, "provider_message_id": None, "status": "failed", "error": "Device token missing"}
        return {"success": True, "provider_message_id": f"mock-push-{uuid.uuid4().hex[:8]}", "status": "sent", "error": None}


class FirebasePushChannel(Channel):
    def send(self, message: str, recipient: dict) -> dict:
        try:
            import firebase_admin
            from firebase_admin import credentials, messaging

            token = recipient.get("device_token")
            if not token:
                raise ValueError("Device token missing")

            app_name = "nexareach"
            try:
                app = firebase_admin.get_app(app_name)
            except ValueError:
                credential_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
                if not credential_path:
                    raise ValueError("FIREBASE_CREDENTIALS_PATH is not configured")
                app = firebase_admin.initialize_app(credentials.Certificate(credential_path), name=app_name)

            result = messaging.send(
                messaging.Message(
                    notification=messaging.Notification(
                        title=os.getenv("PUSH_NOTIFICATION_TITLE", "NexaReach"),
                        body=message
                    ),
                    token=token
                ),
                app=app
            )
            return {"success": True, "provider_message_id": result, "status": "sent", "error": None}
        except Exception as exc:
            return {"success": False, "provider_message_id": None, "status": "failed", "error": str(exc)}
