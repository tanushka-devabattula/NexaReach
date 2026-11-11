from app.models.models import Campaign, CampaignContent, User
from app.schemas.review import ReviewDecisionRequest, ReviewSubmitRequest
from app.services.compliance_service import submit_for_review, decide_review


def make_campaign(db):
    campaign = Campaign(
        name="Review Integration Test",
        objective="Verify campaign review synchronization",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


def make_reviewer(db):
    reviewer = User(
        full_name="Integration Test Reviewer",
        email="review-integration@example.test",
        hashed_password="test-only-hash",
    )
    db.add(reviewer)
    db.commit()
    db.refresh(reviewer)
    return reviewer


def test_campaign_review_approval_approves_linked_content(db):
    campaign = make_campaign(db)
    reviewer = make_reviewer(db)

    review = submit_for_review(
        ReviewSubmitRequest(
            campaign_id=campaign.id,
            content="Health checkups help people stay informed. Contact your local clinic.",
            channel="SMS",
            language="English",
        ),
        db=db,
    )

    assert review.status == "pending_review"
    assert review.campaign_content_id is not None

    content = db.query(CampaignContent).filter_by(
        id=review.campaign_content_id
    ).one()
    assert content.campaign_id == campaign.id
    assert content.status == "in_review"

    updated = decide_review(
        review.id,
        ReviewDecisionRequest(
            decision="approved",
            reviewer_notes="Reviewed and approved.",
        ),
        db=db,
        reviewer_id=reviewer.id,
    )

    db.refresh(content)
    assert updated.status == "approved"
    assert updated.reviewer_id == reviewer.id
    assert content.status == "approved"
    assert content.approved_by == reviewer.id
    assert content.approved_at is not None


def test_campaign_review_rejection_rejects_linked_content(db):
    campaign = make_campaign(db)

    review = submit_for_review(
        ReviewSubmitRequest(
            campaign_id=campaign.id,
            content="Please review this public awareness message.",
            channel="SMS",
            language="English",
        ),
        db=db,
    )

    content = db.query(CampaignContent).filter_by(
        id=review.campaign_content_id
    ).one()

    decide_review(
        review.id,
        ReviewDecisionRequest(decision="rejected"),
        db=db,
    )

    db.refresh(content)
    assert content.status == "rejected"
    assert content.approved_by is None
    assert content.approved_at is None


def test_changes_requested_returns_linked_content_to_draft(db):
    campaign = make_campaign(db)

    review = submit_for_review(
        ReviewSubmitRequest(
            campaign_id=campaign.id,
            content="Please review this draft message.",
            channel="SMS",
            language="English",
        ),
        db=db,
    )

    content = db.query(CampaignContent).filter_by(
        id=review.campaign_content_id
    ).one()

    decide_review(
        review.id,
        ReviewDecisionRequest(
            decision="changes_requested",
            reviewer_notes="Please improve the wording.",
        ),
        db=db,
    )

    db.refresh(content)
    assert content.status == "draft"
    assert content.approved_by is None
    assert content.approved_at is None


def test_existing_campaign_content_is_linked_and_updated_on_review(db):
    campaign = make_campaign(db)
    content = CampaignContent(
        campaign_id=campaign.id,
        content="Original draft",
        language="English",
        channel="SMS",
        status="draft",
    )
    db.add(content)
    db.commit()
    db.refresh(content)

    review = submit_for_review(
        ReviewSubmitRequest(
            campaign_id=campaign.id,
            campaign_content_id=content.id,
            content="Updated reviewed message.",
            channel="SMS",
            language="English",
        ),
        db=db,
    )

    db.refresh(content)
    assert review.campaign_content_id == content.id
    assert content.content == "Updated reviewed message."
    assert content.status == "in_review"
