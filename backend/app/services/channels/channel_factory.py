import os
from dotenv import load_dotenv

load_dotenv()

from .email import MockEmailChannel, SMTPEmailChannel
from .sms import MockSMSChannel, TwilioSMSChannel
from .whatsapp import MockWhatsAppChannel, MetaWhatsAppChannel
from .push import MockPushChannel, FirebasePushChannel


def _use_mock(name: str) -> bool:
    return os.getenv(name, "1").strip().lower() in ("1", "true", "yes", "on")


def get_email_channel():
    return MockEmailChannel() if _use_mock("EMAIL_MOCK") else SMTPEmailChannel()


def get_sms_channel():
    return MockSMSChannel() if _use_mock("SMS_MOCK") else TwilioSMSChannel()


def get_whatsapp_channel():
    return MockWhatsAppChannel() if _use_mock("WHATSAPP_MOCK") else MetaWhatsAppChannel()


def get_push_channel():
    return MockPushChannel() if _use_mock("PUSH_MOCK") else FirebasePushChannel()
