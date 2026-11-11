from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, model_validator


class CampaignContentCreate(BaseModel):
    campaign_id: int = Field(..., description="ID of the associated campaign")
    content: str = Field(min_length=1, description="Message text or template body")
    language: str = Field(default="English", max_length=50, description="Target language")
    channel: str = Field(default="SMS", max_length=50, description="Delivery channel (SMS, EMAIL, etc.)")
    segment_id: int | None = Field(default=None, description="Optional target segment ID")


class CampaignContentDecisionRequest(BaseModel):
    decision: str | None = Field(
        default=None,
        description="Decision: 'approved' or 'rejected'",
    )
    status: str | None = Field(
        default=None,
        description="Alternative field for decision status ('approved' or 'rejected')",
    )
    action: str | None = Field(
        default=None,
        description="Alternative field for decision action ('approve' or 'reject')",
    )

    @model_validator(mode="after")
    def validate_and_normalize_decision(self):
        val = self.decision or self.status or self.action
        if not val or not isinstance(val, str):
            raise ValueError("A decision ('approved' or 'rejected') must be provided.")
        val_clean = val.strip().lower()
        if val_clean in ("approved", "approve"):
            self.decision = "approved"
        elif val_clean in ("rejected", "reject"):
            self.decision = "rejected"
        else:
            raise ValueError(f"Invalid decision '{val}'. Allowed decisions are 'approved' or 'rejected'.")
        return self


class CampaignContentResponse(BaseModel):
    id: int
    campaign_id: int
    language: str
    segment_id: int | None = None
    channel: str
    content: str
    status: str
    approved_by: int | None = None
    approved_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
