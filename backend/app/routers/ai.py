from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ai import (
    AIGenerateRequest,
    AIGenerateResponse,
    AIHistoryResponse,
)
from app.services.ai_service import (
    generate_content,
    list_generation_history,
)

router = APIRouter(prefix="/ai", tags=["AI Generation"])


@router.post(
    "/generate",
    response_model=AIGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate public awareness message content",
)
def generate_ai_content(
    request: AIGenerateRequest,
    db: Session = Depends(get_db),
):
    """
    Generates awareness content tailored for specified channel and tone.
    Uses configured AI provider (OpenAI) if available; otherwise smoothly falls
    back to deterministic offline templates. Offline results are clearly flagged
    with provider='offline-fallback' and is_fallback=True.
    """
    return generate_content(request, db=db)


@router.get(
    "/history",
    response_model=list[AIHistoryResponse],
    summary="Retrieve AI generation history",
)
def get_generation_history(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Returns recent generated messages stored in the database.
    """
    return list_generation_history(db, limit=limit)

