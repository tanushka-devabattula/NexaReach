from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.models import Campaign, CampaignContent, Role, Segment, User
from app.schemas.campaign_content import (
    CampaignContentCreate,
    CampaignContentDecisionRequest,
    CampaignContentResponse,
)

router = APIRouter(tags=["Campaign Content"])


def verify_reviewer_or_admin(user: User, db: Session) -> Role:
    """
    Enforces authorization: Only users with reviewer or admin roles
    can approve or reject campaign content.
    Fails closed for ordinary 'user' accounts or unassigned/unknown roles.
    """
    if not user.role_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: User has no assigned role.",
        )
    role = db.query(Role).filter(Role.id == user.role_id).first()
    if not role or not role.name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: User role cannot be determined.",
        )

    role_name = role.name.strip().lower()
    allowed_roles = {"admin", "reviewer", "compliance_reviewer"}
    if role_name not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Role '{role.name}' is not authorized to approve or reject campaign content. Reviewer or admin role required.",
        )
    return role


@router.post(
    "/campaign-content",
    response_model=CampaignContentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create campaign content in draft status",
)
@router.post(
    "/campaign-contents",
    response_model=CampaignContentResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def create_campaign_content(
    content_data: CampaignContentCreate,
    db: Session = Depends(get_db),
):
    campaign = db.query(Campaign).filter(Campaign.id == content_data.campaign_id).first()
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Campaign #{content_data.campaign_id} not found.",
        )

    if content_data.segment_id is not None:
        segment = db.query(Segment).filter(Segment.id == content_data.segment_id).first()
        if segment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Segment #{content_data.segment_id} not found.",
            )

    new_content = CampaignContent(
        campaign_id=content_data.campaign_id,
        content=content_data.content,
        language=content_data.language or "English",
        channel=content_data.channel or "SMS",
        segment_id=content_data.segment_id,
        status="draft",
        approved_by=None,
        approved_at=None,
    )

    try:
        db.add(new_content)
        db.commit()
        db.refresh(new_content)
        return new_content
    except Exception:
        db.rollback()
        raise


@router.get(
    "/campaign-content",
    response_model=list[CampaignContentResponse],
    status_code=status.HTTP_200_OK,
    summary="List campaign content records",
)
@router.get(
    "/campaign-contents",
    response_model=list[CampaignContentResponse],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def list_campaign_content(
    campaign_id: int | None = Query(default=None, description="Optional campaign ID filter"),
    db: Session = Depends(get_db),
):
    query = db.query(CampaignContent)
    if campaign_id is not None:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign #{campaign_id} not found.",
            )
        query = query.filter(CampaignContent.campaign_id == campaign_id)
    return query.order_by(CampaignContent.id.desc()).all()


@router.get(
    "/campaign-content/{content_id}",
    response_model=CampaignContentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get campaign content by ID",
)
@router.get(
    "/campaign-contents/{content_id}",
    response_model=CampaignContentResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def get_campaign_content(
    content_id: int,
    db: Session = Depends(get_db),
):
    content = db.query(CampaignContent).filter(CampaignContent.id == content_id).first()
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CampaignContent #{content_id} not found.",
        )
    return content


@router.post(
    "/campaign-content/{content_id}/decision",
    response_model=CampaignContentResponse,
    status_code=status.HTTP_200_OK,
    summary="Explicitly approve or reject campaign content",
)
@router.post(
    "/campaign-contents/{content_id}/decision",
    response_model=CampaignContentResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def decide_campaign_content(
    content_id: int,
    decision_data: CampaignContentDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Enforce role authorization (fails closed if not reviewer/admin)
    verify_reviewer_or_admin(current_user, db)

    content = db.query(CampaignContent).filter(CampaignContent.id == content_id).first()
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CampaignContent #{content_id} not found.",
        )

    if content.status not in ("draft", "in_review"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot decide on CampaignContent with status '{content.status}'. Only content in 'draft' or 'in_review' status can be approved or rejected.",
        )

    decision = decision_data.decision
    if decision == "approved":
        content.status = "approved"
        content.approved_by = current_user.id
        content.approved_at = datetime.utcnow()
    elif decision == "rejected":
        content.status = "rejected"
        content.approved_by = None
        content.approved_at = None
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid decision '{decision}'. Must be 'approved' or 'rejected'.",
        )

    try:
        db.commit()
        db.refresh(content)
        return content
    except Exception:
        db.rollback()
        raise


@router.post(
    "/campaign-content/{content_id}/approve",
    response_model=CampaignContentResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve campaign content",
)
@router.post(
    "/campaign-contents/{content_id}/approve",
    response_model=CampaignContentResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def approve_campaign_content(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return decide_campaign_content(
        content_id=content_id,
        decision_data=CampaignContentDecisionRequest(decision="approved"),
        db=db,
        current_user=current_user,
    )


@router.post(
    "/campaign-content/{content_id}/reject",
    response_model=CampaignContentResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject campaign content",
)
@router.post(
    "/campaign-contents/{content_id}/reject",
    response_model=CampaignContentResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def reject_campaign_content(
    content_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return decide_campaign_content(
        content_id=content_id,
        decision_data=CampaignContentDecisionRequest(decision="rejected"),
        db=db,
        current_user=current_user,
    )
