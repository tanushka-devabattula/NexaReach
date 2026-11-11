import os
import sys
import uuid
from unittest.mock import patch

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

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
    Message,
    Role,
    Segment,
    User,
)

# Setup isolated in-memory test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
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


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def seed_base_data():
    db = TestingSessionLocal()
    try:
        # Create users & roles
        admin_role = Role(name="admin", description="Admin")
        db.add(admin_role)
        db.commit()

        user = User(
            full_name="Admin User",
            email="admin@test.com",
            hashed_password="hashed_pwd",
            role_id=admin_role.id,
            is_active=True,
        )
        db.add(user)
        db.commit()

        # Create segments
        seg_hindi = Segment(
            name="Hindi Speakers",
            description="Members preferring Hindi",
            criteria={"language": "Hindi"},
        )
        seg_tamil = Segment(
            name="Tamil Speakers",
            description="Members preferring Tamil",
            criteria={"language": "Tamil"},
        )
        db.add_all([seg_hindi, seg_tamil])
        db.commit()

        # Create audience members
        # 1. Consented, English, has both email and phone
        m1 = AudienceMember(
            full_name="Consented Alice",
            email="alice@example.com",
            phone="+1234567890",
            preferred_language="English",
            consent=True,
        )
        # 2. Consented, Hindi, has phone only
        m2 = AudienceMember(
            full_name="Consented Bob",
            email=None,
            phone="+9876543210",
            preferred_language="Hindi",
            consent=True,
        )
        # 3. Consented, English, has email only (no phone)
        m3 = AudienceMember(
            full_name="Consented Charlie",
            email="charlie@example.com",
            phone=None,
            preferred_language="English",
            consent=True,
        )
        # 4. NOT Consented, English, has both email and phone
        m4 = AudienceMember(
            full_name="Unconsented Dave",
            email="dave@example.com",
            phone="+1122334455",
            preferred_language="English",
            consent=False,
        )
        # 5. NOT Consented, Hindi, has both
        m5 = AudienceMember(
            full_name="Unconsented Eve",
            email="eve@example.com",
            phone="+9988776655",
            preferred_language="Hindi",
            consent=False,
        )
        db.add_all([m1, m2, m3, m4, m5])
        db.commit()

        # Create campaigns
        c_general = Campaign(
            name="General Awareness Campaign",
            objective="General public outreach",
            status="draft",
            segment_id=None,
        )
        c_hindi = Campaign(
            name="Hindi Cohort Campaign",
            objective="Outreach to Hindi speakers",
            status="draft",
            segment_id=seg_hindi.id,
        )
        c_tamil_empty = Campaign(
            name="Tamil Cohort Campaign",
            objective="Outreach to Tamil speakers (none in DB)",
            status="draft",
            segment_id=seg_tamil.id,
        )
        c_no_content = Campaign(
            name="Empty Content Campaign",
            objective="No approved content",
            status="draft",
            segment_id=None,
        )
        db.add_all([c_general, c_hindi, c_tamil_empty, c_no_content])
        db.commit()

        return {
            "c_general_id": c_general.id,
            "c_hindi_id": c_hindi.id,
            "c_tamil_empty_id": c_tamil_empty.id,
            "c_no_content_id": c_no_content.id,
            "m1_id": m1.id,
            "m2_id": m2.id,
            "m3_id": m3.id,
            "m4_id": m4.id,
            "m5_id": m5.id,
        }
    finally:
        db.close()


def run_campaign_send_tests():
    print("--- Starting Campaign Sending Focused Test Suite ---")
    data = seed_base_data()
    db = TestingSessionLocal()

    # 1. Test: Campaign Not Found -> 404
    res = client.post("/campaigns/999999/send")
    assert res.status_code == 404, f"Expected 404, got {res.status_code}: {res.text}"
    print("[PASS] Test 1: Non-existent campaign returns 404 Not Found")

    # 2. Test: No Approved Content -> 400
    res = client.post(f"/campaigns/{data['c_no_content_id']}/send")
    assert res.status_code == 400, f"Expected 400, got {res.status_code}: {res.text}"
    assert "no approved content" in res.json()["detail"].lower()
    print("[PASS] Test 2: Campaign with no approved content returns 400 Bad Request")

    # Add unapproved content (draft, in_review, rejected) to c_no_content and verify it still returns 400
    db.add_all([
        CampaignContent(campaign_id=data["c_no_content_id"], content="Draft", status="draft", channel="SMS"),
        CampaignContent(campaign_id=data["c_no_content_id"], content="Review", status="in_review", channel="SMS"),
        CampaignContent(campaign_id=data["c_no_content_id"], content="Rejected", status="rejected", channel="SMS"),
    ])
    db.commit()
    res = client.post(f"/campaigns/{data['c_no_content_id']}/send")
    assert res.status_code == 400
    print("[PASS] Test 3: Unapproved content (draft, in_review, rejected) is strictly ignored (400 returned)")

    # 3. Test: Mock SMS Send with General Audience
    # Create approved SMS content for c_general (English)
    sms_content = CampaignContent(
        campaign_id=data["c_general_id"],
        content="Dear {{name}}, stay safe and follow health advice.",
        language="English",
        channel="SMS",
        status="approved",
    )
    db.add(sms_content)
    db.commit()

    res = client.post(f"/campaigns/{data['c_general_id']}/send")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    result = res.json()

    # Total considered = 5 (all 5 members in DB)
    assert result["total_audience_considered"] == 5
    # Consented: m1 (has phone, English -> SENT)
    # Consented: m2 (Hindi, no English match -> SKIPPED)
    # Consented: m3 (English, NO phone -> SKIPPED)
    # Unconsented: m4, m5 -> SKIPPED
    # Total sent = 1 (m1), Total skipped = 4
    assert result["sent"] == 1
    assert result["skipped"] == 4
    assert result["failed"] == 0
    assert "SMS" in result["channels"]
    assert result["channels"]["SMS"]["sent"] == 1
    assert len(result["skip_reasons"]) >= 4
    print(f"[PASS] Test 4: General SMS send succeeded (sent={result['sent']}, skipped={result['skipped']})")

    # Verify Message and DeliveryLog persisted in DB
    msg = db.query(Message).filter_by(campaign_id=data["c_general_id"]).first()
    assert msg is not None
    assert msg.audience_member_id == data["m1_id"]
    assert msg.status == "sent"
    assert msg.tracking_id is not None
    assert msg.provider_message_id is not None
    assert msg.provider_message_id.startswith("mock-sms-")
    assert "Consented Alice" in msg.content  # Personalization token replaced!

    log = db.query(DeliveryLog).filter_by(message_id=msg.id).first()
    assert log is not None
    assert log.status == "sent"
    assert log.sent_at is not None
    assert log.provider_message_id == msg.provider_message_id
    print("[PASS] Test 5: Message and DeliveryLog properly created with tracking_id and provider_message_id")

    # 4. Test: Retrying the endpoint prevents duplicate sends
    res_retry = client.post(f"/campaigns/{data['c_general_id']}/send")
    assert res_retry.status_code == 200
    retry_result = res_retry.json()
    assert retry_result["sent"] == 0, f"Expected 0 sent on retry, got {retry_result['sent']}"
    assert retry_result["skipped"] == 5, f"Expected 5 skipped on retry, got {retry_result['skipped']}"
    # Verify no new Message was added
    total_msgs = db.query(Message).filter_by(campaign_id=data["c_general_id"]).count()
    assert total_msgs == 1
    print("[PASS] Test 6: Retry idempotency verified (0 duplicates sent, existing delivery preserved)")

    # 5. Test: Mock Email Send
    # Add an approved EMAIL content to c_general
    email_content = CampaignContent(
        campaign_id=data["c_general_id"],
        content="Dear {{name}}, this is an email update.",
        language="English",
        channel="EMAIL",
        status="approved",
    )
    db.add(email_content)
    db.commit()

    res_email = client.post(f"/campaigns/{data['c_general_id']}/send")
    assert res_email.status_code == 200
    email_result = res_email.json()
    # For SMS: m1 is already sent -> duplicate skip
    # For EMAIL:
    # m1 has consent & email -> SENT
    # m3 has consent & email -> SENT
    # m2 has no email -> skip
    # m4, m5 have no consent -> skip
    assert email_result["channels"]["EMAIL"]["sent"] == 2
    assert email_result["channels"]["SMS"]["sent"] == 0  # SMS already sent earlier
    print(f"[PASS] Test 7: Email channel delivery succeeded (sent={email_result['channels']['EMAIL']['sent']})")

    # 6. Test: Segment filtering & Hindi language matching
    # c_hindi targets Hindi segment.
    # m2 is in Hindi segment, consent=True, has phone.
    # m5 is in Hindi segment, consent=False -> skipped.
    hindi_content = CampaignContent(
        campaign_id=data["c_hindi_id"],
        content="नमस्ते {{name}}, स्वास्थ्य शिविर में भाग लें।",
        language="Hindi",
        channel="SMS",
        status="approved",
    )
    db.add(hindi_content)
    db.commit()

    res_hindi = client.post(f"/campaigns/{data['c_hindi_id']}/send")
    assert res_hindi.status_code == 200
    hindi_result = res_hindi.json()
    assert hindi_result["total_audience_considered"] == 2  # Only m2 and m5 match Hindi segment
    assert hindi_result["sent"] == 1  # m2 sent
    assert hindi_result["skipped"] == 1  # m5 skipped (no consent)
    print(f"[PASS] Test 8: Segment filtering strictly applied (considered={hindi_result['total_audience_considered']}, sent={hindi_result['sent']}, skipped={hindi_result['skipped']})")

    # 7. Test: Segment assigned but matches NO members -> send to nobody (never fallback)
    tamil_content = CampaignContent(
        campaign_id=data["c_tamil_empty_id"],
        content="வணக்கம் {{name}}",
        language="Tamil",
        channel="SMS",
        status="approved",
    )
    db.add(tamil_content)
    db.commit()

    res_tamil = client.post(f"/campaigns/{data['c_tamil_empty_id']}/send")
    assert res_tamil.status_code == 200
    tamil_result = res_tamil.json()
    assert tamil_result["total_audience_considered"] == 0
    assert tamil_result["sent"] == 0
    assert tamil_result["skipped"] == 0
    print("[PASS] Test 9: Segment with no members sends to nobody (never falls back to general audience)")

    # 8. Test: Failed mock provider response handling
    # Create another campaign with an approved SMS content
    c_fail = Campaign(name="Failure Test Campaign", status="draft")
    db.add(c_fail)
    db.commit()

    fail_content = CampaignContent(
        campaign_id=c_fail.id,
        content="Test fail",
        language="English",
        channel="SMS",
        status="approved",
    )
    db.add(fail_content)
    db.commit()

    # Mock get_sms_channel().send to simulate a provider delivery failure
    with patch("app.services.campaign_send_service.get_sms_channel") as mock_get_sms:
        mock_sender = mock_get_sms.return_value
        mock_sender.send.return_value = {
            "success": False,
            "provider_message_id": None,
            "status": "failed",
            "error": "Simulated telco network congestion",
        }

        res_fail = client.post(f"/campaigns/{c_fail.id}/send")
        assert res_fail.status_code == 200
        fail_res_data = res_fail.json()
        assert fail_res_data["failed"] >= 1
        assert fail_res_data["sent"] == 0
        # Ensure per-channel failed count is updated
        assert fail_res_data["channels"]["SMS"]["failed"] >= 1

        # Verify failed Message and DeliveryLog in DB
        fail_msg = db.query(Message).filter_by(campaign_id=c_fail.id).first()
        assert fail_msg is not None
        assert fail_msg.status == "failed"
        assert fail_msg.tracking_id is not None

        fail_log = db.query(DeliveryLog).filter_by(message_id=fail_msg.id).first()
        assert fail_log is not None
        assert fail_log.status == "failed"
        assert fail_log.sent_at is None
        assert "Simulated telco network congestion" in fail_log.provider_response
        print("[PASS] Test 10: Provider failure correctly recorded as failed without sent_at timestamp")
    # 11. Test: Cross-segment content should not be used (different segment content only)
    # Create a new campaign assigned to the Hindi segment but only Tamil content exists.
    hindi_seg = db.query(Segment).filter(Segment.name == "Hindi Speakers").first()
    assert hindi_seg is not None
    c_hindi_wrong = Campaign(name="Hindi Wrong Segment Campaign", status="draft", segment_id=hindi_seg.id)
    db.add(c_hindi_wrong)
    db.commit()
    # Add Tamil approved content to this campaign (segment mismatch)
    tamil_wrong = CampaignContent(
        campaign_id=c_hindi_wrong.id,
        content="வணக்கம் {{name}}",
        language="Tamil",
        channel="SMS",
        status="approved",
    )
    db.add(tamil_wrong)
    db.commit()

    res_cross = client.post(f"/campaigns/{c_hindi_wrong.id}/send")
    assert res_cross.status_code == 200
    cross_res = res_cross.json()
    # No messages should be sent because content language does not match segment language.
    assert cross_res["sent"] == 0
    # Both members in Hindi segment are considered (m2 consented, m5 not consented). They should be skipped.
    assert cross_res["skipped"] >= 1
    print("[PASS] Test 11: Cross-segment content correctly rejected (sent=0)")

    # 12. Test: Duplicate prevention includes failed messages
    c_dup_fail = Campaign(name="DupFail Campaign", status="draft")
    db.add(c_dup_fail)
    db.commit()
    dup_content = CampaignContent(
        campaign_id=c_dup_fail.id,
        content="Test dup",
        language="English",
        channel="SMS",
        status="approved",
    )
    db.add(dup_content)
    db.commit()
    # First send fails
    with patch("app.services.campaign_send_service.get_sms_channel") as mock_get_sms:
        mock_sender = mock_get_sms.return_value
        mock_sender.send.return_value = {
            "success": False,
            "provider_message_id": None,
            "status": "failed",
            "error": "Simulated failure",
        }
        res_first = client.post(f"/campaigns/{c_dup_fail.id}/send")
        assert res_first.status_code == 200
        first_data = res_first.json()
        assert first_data["failed"] == 1
        fail_msg = db.query(Message).filter_by(campaign_id=c_dup_fail.id).first()
        assert fail_msg is not None
        assert fail_msg.status == "failed"
    # Second send should skip due to duplicate (including failed)
    res_second = client.post(f"/campaigns/{c_dup_fail.id}/send")
    assert res_second.status_code == 200
    second_data = res_second.json()
    assert second_data["sent"] == 0
    assert second_data["skipped"] >= 1
    assert any("Duplicate delivery" in r for r in second_data["skip_reasons"])
    print("[PASS] Test 12: Duplicate prevention includes failed messages")

    # 13. Test: Tracking ID uniqueness across multiple messages
    all_tracking_ids = [m.tracking_id for m in db.query(Message).all()]
    assert len(all_tracking_ids) == len(set(all_tracking_ids))
    print(f"[PASS] Test 13: All {len(all_tracking_ids)} generated tracking_ids are globally unique UUIDs")

    db.close()
    print("\n--- ALL 13 FOCUSED CAMPAIGN SEND TESTS PASSED ---")




if __name__ == '__main__':
    # Run on its own: pretend a campaign manager is logged in (routes need a login).
    from types import SimpleNamespace
    from app.core.security import get_current_user
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, full_name="Test Admin", email="admin@example.com",
        is_active=True, role_id=None, role_name="admin",
    )
    run_campaign_send_tests()
