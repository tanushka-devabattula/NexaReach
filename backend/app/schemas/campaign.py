
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CampaignCreate(BaseModel):
    name: str = Field(min_length=3, max_length=150)
    objective: str | None = None
    status: str = "draft"
    segment_id: int | None = None


class CampaignResponse(BaseModel):
    id: int
    name: str
    objective: str | None = None
    status: str
    created_by: int | None = None
    segment_id: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
