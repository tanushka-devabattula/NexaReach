from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.personalization import (
    PersonalizePreviewRequest,
    PersonalizePreviewResponse,
    SegmentVariantRequest,
    SegmentVariantResponse,
)
from app.services.personalization_service import (
    NotFoundError,
    generate_segment_variants,
    preview_personalization,
)
from app.services.translation_service import TranslationProviderError

router = APIRouter(prefix="/personalize", tags=["Personalization & Segments"])


def _run(func, *args):
    try:
        return func(*args)
    except NotFoundError as err:  # member / segment not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    except ValueError as err:  # empty text / unsupported language
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except TranslationProviderError as err:  # translation provider problem: say so
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(err))


@router.post("/preview", response_model=PersonalizePreviewResponse, summary="Fill {{tokens}} using audience data")
def preview_message_personalization(request: PersonalizePreviewRequest, db: Session = Depends(get_db)):
    return _run(preview_personalization, request, db)


@router.post("/variants", response_model=SegmentVariantResponse, summary="Personalized samples for a segment")
def generate_variants_for_segment(request: SegmentVariantRequest, db: Session = Depends(get_db)):
    return _run(generate_segment_variants, request, db)