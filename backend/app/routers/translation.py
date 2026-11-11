from fastapi import APIRouter, Depends, HTTPException, status
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
    TranslationProviderError,
    batch_translate,
    get_supported_languages,
    translate_text,
)

router = APIRouter(tags=["Translation"])


@router.get("/translate/languages", response_model=list[LanguageInfo], summary="Supported languages")
def list_languages():
    return get_supported_languages()


@router.post("/translate", response_model=TranslationResult, summary="Translate text into one language")
@router.post("/ai/translate", response_model=TranslationResult, include_in_schema=False)
@router.post("/ai/content/translate", response_model=TranslationResult, include_in_schema=False)
def translate_endpoint(payload: TranslationRequest, db: Session = Depends(get_db)):
    try:
        return translate_text(payload, db=db)
    except ValueError as err:  # empty text or unsupported language
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except TranslationProviderError as err:  # provider missing / failed: say so honestly
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(err))


@router.post("/translate/batch", response_model=BatchTranslationResponse, summary="Translate one text into many languages")
@router.post("/ai/translate/bulk", response_model=BatchTranslationResponse, include_in_schema=False)
def translate_batch_endpoint(payload: BatchTranslationRequest, db: Session = Depends(get_db)):
    try:
        response = batch_translate(payload, db=db)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    if not response.results:  # nothing worked: report the real reason
        reasons = list(dict.fromkeys(e.detail for e in response.errors))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=" | ".join(reasons) or "No translations were produced.",
        )
    return response
