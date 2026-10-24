from pydantic import BaseModel, Field

from app.schemas.ai import AIGenerateResponse
from app.schemas.analysis import ToneAnalysisResponse
from app.schemas.personalization import SegmentVariantResponse
from app.schemas.review import ComplianceCheckResponse, ReviewResponse
from app.schemas.translation import BatchTranslationResponse


class WorkflowRunRequest(BaseModel):
    prompt: str = Field(min_length=3, description="Topic or objective of awareness message")
    channel: str = Field(default="SMS", description="Channel: SMS, WhatsApp, Email, etc.")
    tone: str = Field(default="Informative", description="Tone: Urgent, Empathetic, Informative, Formal, etc.")
    target_languages: list[str] = Field(
        default_factory=lambda: [
            "Hindi",
            "Kannada",
            "Tamil",
            "Telugu",
            "Marathi",
            "Bengali",
            "Gujarati",
            "Malayalam",
            "Punjabi",
            "Urdu",
        ],
        description="Target Indian languages for multilingual broadcast",
    )
    segment_id: int | None = Field(default=None, description="Optional audience segment ID for personalization")
    campaign_id: int | None = Field(default=None, description="Optional campaign ID to link review and history")
    user_id: int | None = None
    auto_submit_for_review: bool = Field(default=True, description="Whether to register ContentReview record in pending_review status")
    reviewer_notes: str | None = Field(default=None, description="Notes for reviewers")


class WorkflowExecutionResponse(BaseModel):
    status: str = "completed"
    generated_content: AIGenerateResponse
    translations: BatchTranslationResponse
    personalization: SegmentVariantResponse | None = None
    analysis: ToneAnalysisResponse
    compliance: ComplianceCheckResponse
    review: ReviewResponse | None = None

