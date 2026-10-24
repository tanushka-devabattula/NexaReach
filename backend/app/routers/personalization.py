from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Segment
from app.schemas.personalization import (
    PersonalizePreviewRequest,
    PersonalizePreviewResponse,
    SegmentVariantRequest,
    SegmentVariantResponse,
)
from app.services.personalization_service import (
    generate_segment_variants,
    preview_personalization,
)

router = APIRouter(prefix="/personalize", tags=["Personalization & Segments"])


@router.post(
    "/preview",
    response_model=PersonalizePreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview placeholder replacement with audience data",
)
def preview_message_personalization(
    request: PersonalizePreviewRequest,
    db: Session = Depends(get_db),
):
    """
    Substitutes {{name}}, {{phone}}, {{preferred_language}}, etc., using live
    audience member records from SQLite or custom attribute overrides.
    """
    return preview_personalization(request, db=db)


@router.post(
    "/variants",
    response_model=SegmentVariantResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate segment audience variants",
)
def generate_variants_for_segment(
    request: SegmentVariantRequest,
    db: Session = Depends(get_db),
):
    """
    Evaluates segment targeting criteria against audience members and
    generates tailored message variants for real cohort members.
    """
    segment = db.query(Segment).filter(Segment.id == request.segment_id).first()
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Segment with ID {request.segment_id} not found.",
        )

    return generate_segment_variants(request, db=db)

