"""Channel fallback order (WhatsApp -> SMS -> Email).

Each test uses its own in-memory database. The conftest logs us in as a fake admin.
A failing channel is faked by swapping it into svc._CHANNEL_GETTERS.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.models.models import (
    AudienceMember,
    Campaign,
    CampaignContent,
    DeliveryLog,
    DeviceToken,
    Message,
)
from app.services import campaign_send_service as svc


class FailingChannel:
    def send(self, message, recipient):
        return {"success": False, "provider_message_id": None, "error": "provider down"}


class CrashingChannel:
    def send(self, message, recipient):
        raise RuntimeError("boom")


@pytest.fixture
def ctx():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override
    yield TestClient(app), Session
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous
    engine.dispose()


# ------------------------------------------------------------------ helpers
def make_member(Session, name="Asha", phone="+911111111111", email="asha@example.com",
                language="English", consent=True):
    db = Session()
    member = AudienceMember(full_name=name, phone=phone, email=email,
                            preferred_language=language, consent=consent)
    db.add(member)
    db.commit()
    member_id = member.id
    db.close()
    return member_id


def make_campaign(Session, order, channels=("WHATSAPP", "SMS", "EMAIL"), language="English"):
    db = Session()
    campaign = Campaign(name=f"Camp {uuid.uuid4().hex[:5]}", objective="t", status="draft", fallback_order=order)
    db.add(campaign)
    db.commit()
    for channel in channels:
        db.add(CampaignContent(campaign_id=campaign.id, content=f"Hello {{{{name}}}} via {channel}",
                               language=language, channel=channel, status="approved"))
    db.commit()
    campaign_id = campaign.id
    db.close()
    return campaign_id


def messages_of(Session, campaign_id):
    db = Session()
    rows = db.query(Message).filter(Message.campaign_id == campaign_id).order_by(Message.id).all()
    out = [(m.channel, m.status) for m in rows]
    db.close()
    return out


# -------------------------------------------------- saving / reading the order
def test_patch_saves_and_normalizes_order(ctx):
    client, Session = ctx
    campaign_id = make_campaign(Session, None, channels=())
    res = client.patch(f"/campaigns/{campaign_id}", json={"fallback_order": ["whatsapp", "SMS", "sms", "email"]})
    assert res.status_code == 200, res.text
    assert res.json()["fallback_order"] == ["WHATSAPP", "SMS", "EMAIL"]
    assert client.get(f"/campaigns/{campaign_id}").json()["fallback_order"] == ["WHATSAPP", "SMS", "EMAIL"]


def test_patch_rejects_bad_input(ctx):
    client, Session = ctx
    campaign_id = make_campaign(Session, None, channels=())
    assert client.patch(f"/campaigns/{campaign_id}", json={"fallback_order": ["telegram"]}).status_code == 422
    assert client.patch(f"/campaigns/{campaign_id}", json={}).status_code == 400
    assert client.patch(f"/campaigns/{campaign_id}", json={"name": None}).status_code == 400
    assert client.patch(f"/campaigns/{campaign_id}", json={"segment_id": 999}).status_code == 404
    assert client.patch("/campaigns/99999", json={"name": "Nope nope"}).status_code == 404


def test_create_campaign_with_order(ctx):
    client, _ = ctx
    res = client.post("/campaigns", json={"name": "Flood alert", "fallback_order": ["sms", "email"]})
    assert res.status_code == 201, res.text
    assert res.json()["fallback_order"] == ["SMS", "EMAIL"]


# ------------------------------------------------------- the real behaviour
def test_first_channel_works_so_no_fallback(ctx):
    client, Session = ctx
    make_member(Session)
    campaign_id = make_campaign(Session, ["WHATSAPP", "SMS", "EMAIL"])
    data = client.post(f"/campaigns/{campaign_id}/send").json()
    assert data["sent"] == 1 and data["failed"] == 0 and data["fallback_used"] == 0
    assert messages_of(Session, campaign_id) == [("WHATSAPP", "sent")]  # SMS/EMAIL never touched


def test_whatsapp_fails_then_sms_is_used(ctx, monkeypatch):
    client, Session = ctx
    monkeypatch.setitem(svc._CHANNEL_GETTERS, "WHATSAPP", lambda: FailingChannel())
    make_member(Session)
    campaign_id = make_campaign(Session, ["WHATSAPP", "SMS", "EMAIL"])

    res = client.post(f"/campaigns/{campaign_id}/send")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["sent"] == 1 and data["failed"] == 0
    assert data["fallback_used"] == 1
    assert data["attempts"] == 2
    assert data["channels"]["WHATSAPP"] == {"sent": 0, "failed": 1, "skipped": 0}
    assert data["channels"]["SMS"]["sent"] == 1
    assert "EMAIL" not in data["channels"]
    assert messages_of(Session, campaign_id) == [("WHATSAPP", "failed"), ("SMS", "sent")]

    db = Session()  # the failure reason is saved
    failed_log = db.query(DeliveryLog).filter(DeliveryLog.channel == "WHATSAPP").first()
    assert failed_log.provider_response == "provider down"
    db.close()


def test_a_crashing_provider_also_falls_back(ctx, monkeypatch):
    client, Session = ctx
    monkeypatch.setitem(svc._CHANNEL_GETTERS, "WHATSAPP", lambda: CrashingChannel())
    make_member(Session)
    campaign_id = make_campaign(Session, ["WHATSAPP", "SMS"])
    data = client.post(f"/campaigns/{campaign_id}/send").json()
    assert data["sent"] == 1 and data["fallback_used"] == 1
    db = Session()
    assert db.query(DeliveryLog).filter(DeliveryLog.channel == "WHATSAPP").first().provider_response == "boom"
    db.close()


def test_all_channels_fail(ctx, monkeypatch):
    client, Session = ctx
    for name in ("WHATSAPP", "SMS", "EMAIL"):
        monkeypatch.setitem(svc._CHANNEL_GETTERS, name, lambda: FailingChannel())
    make_member(Session)
    campaign_id = make_campaign(Session, ["WHATSAPP", "SMS", "EMAIL"])
    data = client.post(f"/campaigns/{campaign_id}/send").json()
    assert data["sent"] == 0 and data["failed"] == 1 and data["attempts"] == 3
    assert [s for _, s in messages_of(Session, campaign_id)] == ["failed", "failed", "failed"]


def test_member_without_phone_skips_to_email(ctx):
    client, Session = ctx
    make_member(Session, phone=None, email="only-email@example.com")
    campaign_id = make_campaign(Session, ["WHATSAPP", "SMS", "EMAIL"])
    data = client.post(f"/campaigns/{campaign_id}/send").json()
    assert data["sent"] == 1 and data["fallback_used"] == 1
    assert messages_of(Session, campaign_id) == [("EMAIL", "sent")]  # nothing was attempted on phone channels


def test_member_with_no_usable_channel_is_skipped_with_reasons(ctx):
    client, Session = ctx
    make_member(Session, name="Nobody", phone=None, email=None)
    campaign_id = make_campaign(Session, ["WHATSAPP", "SMS", "EMAIL"])
    data = client.post(f"/campaigns/{campaign_id}/send").json()
    assert data["sent"] == 0 and data["skipped"] == 1 and data["attempts"] == 0
    reason = " ".join(data["skip_reasons"])
    assert "Nobody" in reason and "missing phone" in reason and "missing email" in reason
    assert messages_of(Session, campaign_id) == []


def test_no_consent_is_never_messaged(ctx):
    client, Session = ctx
    make_member(Session, consent=False)
    campaign_id = make_campaign(Session, ["WHATSAPP", "SMS"])
    data = client.post(f"/campaigns/{campaign_id}/send").json()
    assert data["sent"] == 0 and data["skipped"] == 1
    assert any("no consent" in r for r in data["skip_reasons"])
    assert messages_of(Session, campaign_id) == []


def test_sending_twice_never_duplicates(ctx):
    client, Session = ctx
    make_member(Session)
    campaign_id = make_campaign(Session, ["WHATSAPP", "SMS"])
    assert client.post(f"/campaigns/{campaign_id}/send").json()["sent"] == 1
    again = client.post(f"/campaigns/{campaign_id}/send").json()
    assert again["sent"] == 0 and again["skipped"] == 1
    assert any("Duplicate delivery prevented" in r for r in again["skip_reasons"])
    assert len(messages_of(Session, campaign_id)) == 1


def test_resend_does_not_retry_a_channel_that_already_failed(ctx, monkeypatch):
    client, Session = ctx
    for name in ("WHATSAPP", "SMS"):
        monkeypatch.setitem(svc._CHANNEL_GETTERS, name, lambda: FailingChannel())
    make_member(Session)
    campaign_id = make_campaign(Session, ["WHATSAPP", "SMS"])
    assert client.post(f"/campaigns/{campaign_id}/send").json()["failed"] == 1
    again = client.post(f"/campaigns/{campaign_id}/send").json()
    assert again["attempts"] == 0 and again["skipped"] == 1
    assert len(messages_of(Session, campaign_id)) == 2  # still just the two original attempts


def test_member_language_decides_which_content_is_used(ctx):
    client, Session = ctx
    make_member(Session, name="Hindi member", language="Hindi")
    campaign_id = make_campaign(Session, ["WHATSAPP", "SMS"], language="English")  # only English content exists
    data = client.post(f"/campaigns/{campaign_id}/send").json()
    assert data["sent"] == 0 and data["skipped"] == 1
    assert "no approved Hindi content" in " ".join(data["skip_reasons"])


def test_push_is_used_only_when_a_device_token_exists(ctx):
    client, Session = ctx
    with_token = make_member(Session, name="Has token", email="a@example.com")
    make_member(Session, name="No token", email="b@example.com")
    db = Session()
    db.add(DeviceToken(audience_member_id=with_token, token="tok-1", platform="web", active=True))
    db.commit()
    db.close()
    campaign_id = make_campaign(Session, ["PUSH", "SMS"], channels=("PUSH", "SMS"))
    data = client.post(f"/campaigns/{campaign_id}/send").json()
    assert data["sent"] == 2 and data["fallback_used"] == 1
    assert data["channels"]["PUSH"]["sent"] == 1 and data["channels"]["SMS"]["sent"] == 1


# ----------------------------------------- the saved order is what controls it
def test_without_an_order_every_content_goes_out_on_its_own_channel(ctx):
    client, Session = ctx
    make_member(Session)
    campaign_id = make_campaign(Session, None, channels=("WHATSAPP", "SMS"))
    data = client.post(f"/campaigns/{campaign_id}/send").json()
    assert data["sent"] == 2 and data["fallback_used"] == 0
    assert sorted(messages_of(Session, campaign_id)) == [("SMS", "sent"), ("WHATSAPP", "sent")]


def test_changing_the_order_changes_who_is_used_first(ctx):
    client, Session = ctx
    make_member(Session)
    campaign_id = make_campaign(Session, ["WHATSAPP", "SMS"])
    assert client.patch(f"/campaigns/{campaign_id}", json={"fallback_order": ["sms", "whatsapp"]}).status_code == 200
    client.post(f"/campaigns/{campaign_id}/send")
    assert messages_of(Session, campaign_id) == [("SMS", "sent")]