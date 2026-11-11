from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

ALLOWED_CHANNELS = ("WHATSAPP", "SMS", "EMAIL", "PUSH")


def _clean_channel_order(value):
    if value is None:
        return None

    cleaned = []
    for item in value:
        name = str(item).strip().upper()
        if name not in ALLOWED_CHANNELS:
            raise ValueError(
                f"Unsupported channel '{item}'. Allowed: {', '.join(ALLOWED_CHANNELS)}"
            )
        if name not in cleaned:
            cleaned.append(name)
    return cleaned


class CampaignCreate(BaseModel):
    name: str = Field(min_length=3, max_length=150)
    objective: str | None = None
    status: str = "draft"
    segment_id: int | None = None
    template_id: int | None = None
    fallback_order: list[str] | None = None
    scheduled_at: datetime | None = None

    @field_validator("fallback_order")
    @classmethod
    def _check_order(cls, value):
        return _clean_channel_order(value)


class CampaignUpdate(BaseModel):
    """PATCH body: send only the fields you want to change."""
    name: str | None = Field(default=None, min_length=3, max_length=150)
    objective: str | None = None
    status: str | None = None
    segment_id: int | None = None
    template_id: int | None = None
    fallback_order: list[str] | None = None
    scheduled_at: datetime | None = None

    @field_validator("fallback_order")
    @classmethod
    def _check_order(cls, value):
        return _clean_channel_order(value)


class CampaignResponse(BaseModel):
    id: int
    name: str
    objective: str | None = None
    status: str
    created_by: int | None = None
    segment_id: int | None = None
    template_id: int | None = None
    fallback_order: list[str] | None = None
    created_at: datetime

    scheduled_at: datetime | None = None
    schedule_status: str = "not_scheduled"
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: datetime | None = None
    last_run_at: datetime | None = None
    last_error: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ChannelDeliverySummary(BaseModel):
    sent: int = 0
    failed: int = 0
    skipped: int = 0


class CampaignSendResponse(BaseModel):
    campaign_id: int
    total_audience_considered: int
    sent: int
    failed: int
    skipped: int
    queued: int = 0
    sent_count: int | None = None
    failed_count: int | None = None
    skipped_count: int | None = None
    total_considered: int | None = None
    channels: dict[str, ChannelDeliverySummary] = Field(default_factory=dict)
    per_channel_summary: dict[str, dict[str, int]] = Field(default_factory=dict)
    skip_reasons: list[str] = Field(default_factory=list)
    fallback_order: list[str] = Field(default_factory=list)
    fallback_used: int = 0
    attempts: int = 0

    model_config = ConfigDict(from_attributes=True)