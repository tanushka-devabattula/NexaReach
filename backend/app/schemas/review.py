from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ComplianceIssue(BaseModel):
    rule: str
    severity: str = Field(description="error, warning, or info")
    message: str
    passed: bool


class ComplianceCheckRequest(BaseModel):
    content: str = Field(min_length=1, description="Message text to audit")
    channel: str = Field(default="SMS", description="Delivery channel (SMS, WhatsApp, Email, etc.)")
    subject: str | None = Field(default=None, description="Optional subject line for email")
    language: str = Field(default="English")


class ComplianceCheckResponse(BaseModel):
    passed: bool
    score: int = Field(ge=0, le=100)
    issues: list[ComplianceIssue]
    character_count: int
    max_recommended_characters: int
    contains_opt_out: bool


class ReviewSubmitRequest(BaseModel):
    campaign_id: int | None = None
    template_id: int | None = None
    content: str = Field(min_length=1)
    channel: str = "SMS"
    language: str = "English"
    reviewer_notes: str | None = None


class ReviewDecisionRequest(BaseModel):
    decision: str = Field(description="'approved', 'rejected', or 'changes_requested'")
    reviewer_notes: str | None = None


class ReviewResponse(BaseModel):
    id: int
    campaign_id: int | None = None
    template_id: int | None = None
    reviewer_id: int | None = None
    status: str
    compliance_score: int
    compliance_issues: list[dict] | None = None
    readability_metrics: dict | None = None
    reviewer_notes: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

