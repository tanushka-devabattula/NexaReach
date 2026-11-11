from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.ai_service import AIProviderError, generate_content, list_generation_history

router = APIRouter(tags=["AI Studio"])


class AIGeneratePayload(BaseModel):
    prompt: Optional[str] = ""
    topic: Optional[str] = ""
    tone: Optional[str] = "Informative"
    channel: Optional[str] = "SMS"
    category: Optional[str] = "Public Health"
    target_language: Optional[str] = "English"
    target_audience: Optional[str] = "General Public"
    variations: int = Field(default=1, ge=1, le=3)


@router.post("/ai/generate", summary="Generate a campaign message with AI")
@router.post("/generate", include_in_schema=False)
@router.post("/content/generate", include_in_schema=False)
@router.post("/generate-content", include_in_schema=False)
def ai_generate_endpoint(payload: AIGeneratePayload, db: Session = Depends(get_db)):
    try:
        return generate_content(
            prompt=payload.prompt or payload.topic or "",
            category=payload.category or "Public Health",
            target_language=payload.target_language or "English",
            tone=payload.tone,
            channel=payload.channel,
            audience=payload.target_audience or "General Public",
            variations=payload.variations,
            db=db,
        )
    except ValueError as err:  # empty prompt
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except AIProviderError as err:  # key missing / provider failed: say so honestly
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(err))


@router.get("/ai/history", summary="Recent AI generations")
@router.get("/history", include_in_schema=False)
@router.get("/generation-history", include_in_schema=False)
def ai_history_endpoint(limit: int = Query(default=10, ge=1, le=100), db: Session = Depends(get_db)):
    return list_generation_history(db=db, limit=limit)