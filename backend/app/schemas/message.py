
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    campaign_id: int = Field(gt=0)
    audience_member_id: int = Field(gt=0)
    template_id: int | None = None
    channel: str = Field(min_length=2, max_length=50)
    language: str = Field(default="English", max_length=50)
    content: str = Field(min_length=1)


class MessageResponse(BaseModel):
    id: int
    campaign_id: int
    audience_member_id: int
    template_id: int | None = None
    channel: str
    language: str
    content: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
