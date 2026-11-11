"""Task 14 backend tests: WhatsApp webhooks, push tokens, campaign send/fallback.

Uses its own in-memory database. The autouse fixture below installs that database for
EACH test and puts back whatever was there before (other test files share the app).
"""
import hashlib
import hmac
import json
import os
import sys
import uuid
from datetime import datetime

import pytest

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.models import (
    AudienceMember,
    Campaign,
    CampaignContent,
    DeliveryLog,
    DeviceToken,
    Feedback,
    Message,
)

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def use_this_files_database():
    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    yield
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


client = TestClient(app)


# ------------------------------------------------------------------ helpers
def create_message(provider_id: str) -> int:
    db = TestingSessionLocal()
    msg = Message(
        campaign_id=1,
        audience_member_id=1,
        template_id=None,
        channel="WHATSAPP",
        language="en",
        content="test",
        status="sent",
        tracking_id=str(uuid.uuid4()),
        provider_message_id=provider_id,
        created_at=datetime.utcnow(),
    )
    db.add(msg)
    db.flush()
    db.add(
        DeliveryLog(
            message_id=msg.id,
            channel="WHATSAPP",
            status="sent",
            provider_response="mock",
            provider_message_id=provider_id,
            sent_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
    )
    db.commit()
    message_id = msg.id  # read BEFORE closing the session
    db.close()
    return message_id


def create_member(**kw) -> int:
    db = TestingSessionLocal()
    member = AudienceMember(
        full_name=kw.get("name", "Test User"),
        email=kw.get("email", f"{uuid.uuid4().hex[:8]}@example.com"),
        phone=kw.get("phone", "+123456"),
        preferred_language="English",
        consent=kw.get("consent", False),
    )
    db.add(member)
    db.commit()
    member_id = member.id
    db.close()
    return member_id


def signed_post(path, payload, secret):
    body = json.dumps(payload).encode()  # sign the exact bytes we send
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return client.post(
        path,
        content=body,
        headers={"Content-Type": "application/json", "X-WhatsApp-Signature": signature},
    )


# ----------------------------------------------------------- status webhook
def test_whatsapp_status_webhook_success(monkeypatch):
    monkeypatch.setenv("WHATSAPP_WEBHOOK_SECRET", "supersecret")
    create_message("prov-123")
    res = signed_post(
        "/webhook/whatsapp/status",
        {"provider_message_id": "prov-123", "status": "delivered"},
        "supersecret",
    )
    assert res.status_code == 200, res.text
    assert res.json()["detail"] == "WhatsApp status webhook processed"
    assert res.json()["matched"] is True

    db = TestingSessionLocal()
    msg = db.query(Message).filter(Message.provider_message_id == "prov-123").first()
    assert msg.status == "delivered"
    log = db.query(DeliveryLog).filter(DeliveryLog.message_id == msg.id).first()
    assert log.status == "delivered"
    db.close()


def test_whatsapp_status_webhook_wrong_signature_is_403(monkeypatch):
    monkeypatch.setenv("WHATSAPP_WEBHOOK_SECRET", "supersecret")
    res = signed_post(
        "/webhook/whatsapp/status",
        {"provider_message_id": "x", "status": "delivered"},
        "a-different-secret",
    )
    assert res.status_code == 403


def test_whatsapp_status_webhook_unknown_status_is_400(monkeypatch):
    monkeypatch.delenv("WHATSAPP_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("WHATSAPP_MOCK", "1")
    res = client.post("/webhook/whatsapp/status", json={"provider_message_id": "x", "status": "banana"})
    assert res.status_code == 400


def test_whatsapp_status_webhook_fail_secret_missing(monkeypatch):
    monkeypatch.setenv("WHATSAPP_MOCK", "0")
    monkeypatch.delenv("WHATSAPP_WEBHOOK_SECRET", raising=False)
    res = client.post("/webhook/whatsapp/status", json={"provider_message_id": "any", "status": "delivered"})
    assert res.status_code == 403


# ------------------------------------------------------------ reply webhook
def test_whatsapp_reply_is_stored_as_feedback_on_the_original_message(monkeypatch):
    monkeypatch.delenv("WHATSAPP_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("WHATSAPP_MOCK", "1")
    message_id = create_message("prov-orig-1")
    res = client.post(
        "/webhook/whatsapp/reply",
        json={"text": "Hello reply", "provider_message_id": "rep-456", "context_message_id": "prov-orig-1"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["matched"] is True

    db = TestingSessionLocal()
    fb = db.query(Feedback).filter(Feedback.comment == "Hello reply").first()
    assert fb is not None
    assert fb.message_id == message_id
    db.close()


def test_whatsapp_reply_matched_by_sender_phone(monkeypatch):
    monkeypatch.delenv("WHATSAPP_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("WHATSAPP_MOCK", "1")
    member_id = create_member(phone="+919876543210", consent=True)
    db = TestingSessionLocal()
    msg = Message(campaign_id=1, audience_member_id=member_id, channel="WHATSAPP", language="English",
                  content="hi", status="sent", provider_message_id=f"p-{uuid.uuid4().hex[:6]}")
    db.add(msg)
    db.commit()
    message_id = msg.id
    db.close()

    res = client.post("/webhook/whatsapp/reply", json={"text": "Thanks, I will come", "from": "+919876543210"})
    assert res.status_code == 200
    assert res.json()["matched"] is True
    db = TestingSessionLocal()
    fb = db.query(Feedback).filter(Feedback.comment == "Thanks, I will come").first()
    assert fb.message_id == message_id and fb.audience_member_id == member_id
    db.close()


def test_whatsapp_reply_that_matches_nothing_is_not_stored(monkeypatch):
    monkeypatch.delenv("WHATSAPP_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("WHATSAPP_MOCK", "1")
    res = client.post("/webhook/whatsapp/reply", json={"text": "who am I replying to?", "from": "+000"})
    assert res.status_code == 200
    assert res.json()["matched"] is False
    db = TestingSessionLocal()
    assert db.query(Feedback).filter(Feedback.comment == "who am I replying to?").count() == 0
    db.close()


def test_whatsapp_reply_without_text_is_400(monkeypatch):
    monkeypatch.delenv("WHATSAPP_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("WHATSAPP_MOCK", "1")
    assert client.post("/webhook/whatsapp/reply", json={"from": "+1"}).status_code == 400


# --------------------------------------------------------------------- push
def test_push_register_duplicate_updates():
    first, second = create_member(), create_member()
    token = f"dev-token-{uuid.uuid4().hex[:6]}"
    res1 = client.post("/push/register", json={"audience_member_id": first, "token": token, "platform": "web"})
    assert res1.status_code == 200, res1.text
    res2 = client.post("/push/register", json={"audience_member_id": second, "token": token, "platform": "android"})
    assert res2.status_code == 200
    db = TestingSessionLocal()
    rows = db.query(DeviceToken).filter(DeviceToken.token == token).all()
    assert len(rows) == 1  # same token is never stored twice
    assert rows[0].audience_member_id == second
    assert rows[0].platform == "android"
    db.close()


def test_push_register_by_email_and_error_cases():
    email = f"{uuid.uuid4().hex[:8]}@example.com"
    member_id = create_member(email=email)
    ok = client.post("/push/register", json={"email": email.upper(), "token": "tok-email-1"})
    assert ok.status_code == 200 and ok.json()["audience_member_id"] == member_id
    assert client.post("/push/register", json={"email": "nobody@example.com", "token": "t2"}).status_code == 404
    assert client.post("/push/register", json={"token": "t3"}).status_code == 400
    assert client.post("/push/register", json={"audience_member_id": 1}).status_code == 422  # token missing


def test_push_unregister():
    member_id = create_member()
    token = f"dev-token-{uuid.uuid4().hex[:6]}"
    client.post("/push/register", json={"audience_member_id": member_id, "token": token, "platform": "web"})
    res = client.post("/push/unregister", json={"token": token})
    assert res.status_code == 200, res.text
    db = TestingSessionLocal()
    assert db.query(DeviceToken).filter(DeviceToken.token == token).first().active is False
    db.close()
    assert client.post("/push/unregister", json={"token": "never-registered"}).status_code == 404


# ------------------------------------------------- send + duplicate prevention
def test_send_uses_consent_and_prevents_duplicates():
    """Only the consenting member is sent to, and a second send never repeats it.
    (Channel FALLBACK order is not built yet - it gets its own tests when it is.)"""
    consenting = create_member(name="Consenting User", consent=True, phone="+123456")
    create_member(name="No Consent User", consent=False, phone="+654321")

    db = TestingSessionLocal()
    campaign = Campaign(name=f"WhatsApp Test {uuid.uuid4().hex[:4]}", objective="test", status="draft", segment_id=None)
    db.add(campaign)
    db.commit()
    db.add(CampaignContent(campaign_id=campaign.id, content="WhatsApp message {{name}}",
                           language="English", channel="WHATSAPP", status="approved"))
    db.commit()
    campaign_id = campaign.id
    db.close()

    res = client.post(f"/campaigns/{campaign_id}/send")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["channels"]["WHATSAPP"]["sent"] >= 1
    assert any("no consent" in reason for reason in data["skip_reasons"])

    db = TestingSessionLocal()
    msg = db.query(Message).filter(Message.campaign_id == campaign_id, Message.audience_member_id == consenting).first()
    assert msg is not None and msg.content == "WhatsApp message Consenting User"
    assert msg.tracking_id and msg.provider_message_id.startswith("mock-whatsapp-")
    db.close()

    res2 = client.post(f"/campaigns/{campaign_id}/send")
    data2 = res2.json()
    assert res2.status_code == 200
    assert data2["channels"]["WHATSAPP"]["sent"] == 0
    assert data2["channels"]["WHATSAPP"]["skipped"] >= 1


def test_existing_campaign_send_suite():
    import test_campaign_send as cs

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = cs.override_get_db  # that suite seeds ITS own database
    try:
        cs.run_campaign_send_tests()
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous