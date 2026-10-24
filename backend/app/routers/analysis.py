from fastapi import APIRouter, status

from app.schemas.analysis import (
    ToneAnalysisRequest,
    ToneAnalysisResponse,
    ToneImprovementRequest,
    ToneImprovementResponse,
)
from app.services.analysis_service import (
    analyze_tone_and_readability,
    improve_tone,
)

router = APIRouter(tags=["Tone & Readability Analysis"])


@router.post(
    "/analysis/tone-readability",
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


@router.post(
    "/ai/improve-tone",
    response_model=ToneImprovementResponse,
    status_code=status.HTTP_200_OK,
    summary="Optimize and rewrite content to match target tone and channel constraints",
)
def improve_content_tone(request: ToneImprovementRequest):
    """
    Rewrites content to match requested tone and channel constraints (e.g. SMS <= 160 chars).
    Returns original text, rewritten text, and actionable improvement recommendations.
    """
    return improve_tone(request)


@router.post(
    "/analysis/improve-tone",
    response_model=ToneImprovementResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def improve_content_tone_alias(request: ToneImprovementRequest):
    return improve_tone(request)

