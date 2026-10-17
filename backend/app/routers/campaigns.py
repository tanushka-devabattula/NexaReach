
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Campaign
from app.schemas.campaign import CampaignCreate, CampaignResponse

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_campaign(
    campaign_data: CampaignCreate,
    db: Session = Depends(get_db),
):
    campaign = Campaign(
        name=campaign_data.name,
        objective=campaign_data.objective,
        status=campaign_data.status,
        segment_id=campaign_data.segment_id,
    )

    db.add(campaign)
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
