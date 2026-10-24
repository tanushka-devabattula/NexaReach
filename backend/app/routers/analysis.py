from fastapi import APIRouter, status

from app.schemas.analysis import (
    ToneAnalysisRequest,
    ToneAnalysisResponse,
)
from app.services.analysis_service import analyze_tone_and_readability

router = APIRouter(prefix="/analysis", tags=["Tone & Readability Analysis"])


@router.post(
    "/tone-readability",
    response_model=ToneAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze readability, clarity score, tone, and sentiment",
)
def analyze_content(request: ToneAnalysisRequest):
    """
    Computes Flesch Reading Ease, Flesch-Kincaid Grade Level, sentence metrics,
    tone distribution, sentiment, and actionable public awareness clarity suggestions.
    """
    return analyze_tone_and_readability(request)

