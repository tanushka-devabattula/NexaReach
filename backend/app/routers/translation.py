from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.translation import (
    BatchTranslationRequest,
    BatchTranslationResponse,
    LanguageInfo,
    TranslationRequest,
    TranslationResult,
)
from app.services.translation_service import (
    batch_translate,
    get_supported_languages,
    translate_text,
)

router = APIRouter(prefix="/translate", tags=["Multilingual Translation"])


@router.get(
    "/languages",
    response_model=list[LanguageInfo],
    summary="List all supported Indian languages",
)
def list_languages():
    """
    Returns list of 10 supported Indian languages (Hindi, Kannada, Tamil,
    Telugu, Marathi, Bengali, Gujarati, Malayalam, Punjabi, Urdu) + English,
    including directional metadata (is_rtl and direction='rtl' for Urdu).
    """
    return get_supported_languages()


@router.post(
    "",
    response_model=TranslationResult,
    status_code=status.HTTP_200_OK,
    summary="Translate message into a target Indian language",
)
def translate_message(
    request: TranslationRequest,
    db: Session = Depends(get_db),
):
    """
    Translates a message while preserving placeholders like {{name}} and URLs.
    Includes bidirectional safe formatting (bidi_safe_text) and RTL flags for Urdu.
    """
    return translate_text(request, db=db)


@router.post(
    "/batch",
    response_model=BatchTranslationResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch translate message into multiple Indian languages",
)
def batch_translate_message(
    request: BatchTranslationRequest,
    db: Session = Depends(get_db),
):
    """
    Translates a message across multiple Indian languages simultaneously
    (defaults to all 10 supported Indian languages if not specified).
    """
    return batch_translate(request, db=db)

