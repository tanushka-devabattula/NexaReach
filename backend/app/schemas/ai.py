from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AIGenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, description="Topic, objective, or draft idea")
    channel: str = Field(default="SMS", description="SMS, WhatsApp, Email, Social Media")
    tone: str = Field(default="Informative", description="Informative, Urgent, Empathetic, Formal, Persuasive, Casual")
    target_audience: str | None = Field(default="General Public", description="Target cohort description")
    campaign_id: int | None = None
    user_id: int | None = None
    variations: int = Field(default=2, ge=1, le=5, description="Number of variations to generate")


class AIGenerateResponse(BaseModel):
    content: str
    variations: list[str] = []
    channel: str
    tone: str
    provider: str
    is_fallback: bool
    model: str | None = None
    history_id: int | None = None
    created_at: datetime


class AIHistoryResponse(BaseModel):
    id: int
    user_id: int | None = None
    campaign_id: int | None = None
    prompt: str
    channel: str | None = None
    tone: str | None = None
    language: str
    generated_content: str
    provider: str
    is_fallback: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

