
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import AudienceMember, Campaign, CampaignContent, Segment
from app.schemas.segment import SegmentCreate, SegmentResponse, SegmentUpdate

router = APIRouter(prefix="/segments", tags=["Segments"])


@router.post(
    "",
    response_model=SegmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_segment(
    data: SegmentCreate,
    db: Session = Depends(get_db),
):
    existing = db.query(Segment).filter(Segment.name == data.name).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A segment with this name already exists.",
        )

    segment = Segment(
        name=data.name,
        description=data.description,
        criteria=data.criteria,
    )

    db.add(segment)
    db.commit()
    db.refresh(segment)
    return segment


@router.get("", response_model=list[SegmentResponse])
def list_segments(db: Session = Depends(get_db)):
    return db.query(Segment).order_by(Segment.id.desc()).all()


@router.get("/{segment_id}", response_model=SegmentResponse)
def get_segment(
    segment_id: int,
    db: Session = Depends(get_db),
):
    segment = db.query(Segment).filter(Segment.id == segment_id).first()

    if segment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segment not found.",
        )

    return segment


@router.get("/{segment_id}/preview")
def preview_segment(
    segment_id: int,
    db: Session = Depends(get_db),
):
    """Return aggregate counts for the members matching a segment."""
    from app.services.personalization_service import members_matching_segment

    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    if segment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segment not found.",
        )

    matched = members_matching_segment(segment, db)
    by_language = {}

    for member in matched:
        language = member.preferred_language or "Unspecified"
        by_language[language] = by_language.get(language, 0) + 1

    return {
        "segment_id": segment.id,
        "segment_name": segment.name,
        "criteria": segment.criteria or {},
        "total_audience": db.query(AudienceMember).count(),
        "total_matched_members": len(matched),
        "consented_members": sum(bool(member.consent) for member in matched),
        "members_with_phone": sum(bool(member.phone) for member in matched),
        "members_with_email": sum(bool(member.email) for member in matched),
        "by_language": by_language,
    }


@router.patch("/{segment_id}", response_model=SegmentResponse)
def update_segment(
    segment_id: int,
    data: SegmentUpdate,
    db: Session = Depends(get_db),
):
    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    if segment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segment not found.",
        )

    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    if "criteria" in changes and changes["criteria"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Criteria must be a JSON object.",
        )

    if "name" in changes:
        if not changes["name"] or not changes["name"].strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Segment name cannot be empty.",
            )

        duplicate = (
            db.query(Segment)
            .filter(Segment.name == changes["name"], Segment.id != segment_id)
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A segment with this name already exists.",
            )

    for field, value in changes.items():
        setattr(segment, field, value)

    db.commit()
    db.refresh(segment)
    return segment


@router.delete("/{segment_id}")
def delete_segment(
    segment_id: int,
    db: Session = Depends(get_db),
):
    segment = db.query(Segment).filter(Segment.id == segment_id).first()
    if segment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segment not found.",
        )

    used_by_campaign = (
        db.query(Campaign.id)
        .filter(Campaign.segment_id == segment_id)
        .first()
    )
    used_by_content = (
        db.query(CampaignContent.id)
        .filter(CampaignContent.segment_id == segment_id)
        .first()
    )

    if used_by_campaign or used_by_content:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This segment is used by a campaign or campaign content and cannot be deleted.",
        )

    db.delete(segment)
    db.commit()
    return {"message": "Segment deleted successfully.", "segment_id": segment_id}
