
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import (
    Campaign, CampaignContent, ContentReview, Message,
    Segment, Template, TranslationRecord,
)
from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignSendResponse,
    CampaignUpdate,
)
from app.core.security import require_role
from app.services.campaign_send_service import send_campaign_messages

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


def to_utc_naive(value):
    """Convert datetime to naive UTC for consistent database storage."""
    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc).replace(tzinfo=None)


@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_campaign(
    campaign_data: CampaignCreate,
    db: Session = Depends(get_db),
):
    selected_template = None
    if campaign_data.template_id is not None:
        selected_template = (
            db.query(Template)
            .filter(Template.id == campaign_data.template_id)
            .first()
        )
        if selected_template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found.",
            )

    scheduled = to_utc_naive(campaign_data.scheduled_at)

    if scheduled is not None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if scheduled <= now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scheduled time must be in the future.",
            )

    campaign = Campaign(
        name=campaign_data.name,
        objective=campaign_data.objective,
        status=campaign_data.status,
        segment_id=campaign_data.segment_id,
        template_id=campaign_data.template_id,
        fallback_order=campaign_data.fallback_order,
        scheduled_at=scheduled,
        schedule_status=(
            "scheduled" if scheduled else "not_scheduled"
        ),
    )

    db.add(campaign)
    db.flush()

    if selected_template is not None:
        db.add(
            CampaignContent(
                campaign_id=campaign.id,
                content=selected_template.body,
                language=selected_template.language or "English",
                channel=(selected_template.channel or "SMS").strip().upper(),
                segment_id=campaign.segment_id,
                status="draft",
            )
        )

    db.commit()
    db.refresh(campaign)

    return campaign


@router.get("", response_model=list[CampaignResponse])
def list_campaigns(db: Session = Depends(get_db)):
    return (
        db.query(Campaign)
        .order_by(Campaign.id.desc())
        .all()
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id)
        .first()
    )

    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    return campaign


@router.patch(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Update a campaign",
    dependencies=[
        Depends(require_role("admin", "campaign_manager"))
    ],
)
def update_campaign(
    campaign_id: int,
    data: CampaignUpdate,
    db: Session = Depends(get_db),
):
    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id)
        .first()
    )

    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )

    changes = data.model_dump(exclude_unset=True)
    old_template_id = campaign.template_id
    selected_template = None

    if changes.get("template_id") is not None:
        selected_template = (
            db.query(Template)
            .filter(Template.id == changes["template_id"])
            .first()
        )
        if selected_template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found.",
            )

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    for required in ("name", "status"):
        if required in changes and changes[required] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{required} cannot be empty",
            )

    if changes.get("segment_id") is not None:
        segment = (
            db.query(Segment)
            .filter(Segment.id == changes["segment_id"])
            .first()
        )

        if segment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Segment not found",
            )

    if "scheduled_at" in changes:
        scheduled = to_utc_naive(changes["scheduled_at"])

        if scheduled is not None:
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            if scheduled <= now:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Scheduled time must be in the future.",
                )

        campaign.scheduled_at = scheduled
        campaign.schedule_status = (
            "scheduled" if scheduled else "not_scheduled"
        )
        campaign.retry_count = 0
        campaign.next_retry_at = None
        campaign.last_error = None

    for field, value in changes.items():
        if field != "scheduled_at":
            setattr(campaign, field, value)

    if selected_template is not None and old_template_id != selected_template.id:
        db.add(
            CampaignContent(
                campaign_id=campaign.id,
                content=selected_template.body,
                language=selected_template.language or "English",
                channel=(selected_template.channel or "SMS").strip().upper(),
                segment_id=campaign.segment_id,
                status="draft",
            )
        )

    db.commit()
    db.refresh(campaign)

    return campaign


@router.post(
    "/{campaign_id}/send",
    response_model=CampaignSendResponse,
    status_code=status.HTTP_200_OK,
    summary="Send approved campaign content to eligible audience members",
    dependencies=[
        Depends(require_role("admin", "campaign_manager"))
    ],
)
def send_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    return send_campaign_messages(
        campaign_id=campaign_id,
        db=db,
    )


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a campaign with no dependent records",
    dependencies=[Depends(require_role("admin", "campaign_manager"))],
)
def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found.",
        )

    dependent_records = [
        ("campaign content", db.query(CampaignContent.id).filter(CampaignContent.campaign_id == campaign_id).first()),
        ("messages", db.query(Message.id).filter(Message.campaign_id == campaign_id).first()),
        ("content reviews", db.query(ContentReview.id).filter(ContentReview.campaign_id == campaign_id).first()),
        ("translation records", db.query(TranslationRecord.id).filter(TranslationRecord.campaign_id == campaign_id).first()),
    ]
    used_by = [label for label, record in dependent_records if record is not None]

    if used_by:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign cannot be deleted because it has associated "
                   + ", ".join(used_by)
                   + ". Preserve it to retain its audit history.",
        )

    db.delete(campaign)
    db.commit()
    return {"message": "Campaign deleted successfully.", "campaign_id": campaign_id}


@router.post(
    "/{campaign_id}/clone",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Clone a campaign and its content as drafts",
    dependencies=[
        Depends(require_role("admin", "campaign_manager"))
    ],
)
def clone_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    original = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id)
        .first()
    )

    if original is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found.",
        )

    cloned = Campaign(
        name=f"{original.name} (Copy)",
        objective=original.objective,
        status="draft",
        created_by=original.created_by,
        segment_id=original.segment_id,
        template_id=original.template_id,
        fallback_order=original.fallback_order,
        scheduled_at=None,
        schedule_status="not_scheduled",
        retry_count=0,
        max_retries=original.max_retries,
        next_retry_at=None,
        last_run_at=None,
        last_error=None,
    )

    db.add(cloned)
    db.flush()

    original_contents = (
        db.query(CampaignContent)
        .filter(CampaignContent.campaign_id == original.id)
        .all()
    )

    for item in original_contents:
        db.add(
            CampaignContent(
                campaign_id=cloned.id,
                language=item.language,
                segment_id=item.segment_id,
                channel=item.channel,
                content=item.content,
                status="draft",
                approved_by=None,
                approved_at=None,
            )
        )

    db.commit()
    db.refresh(cloned)

    return cloned
