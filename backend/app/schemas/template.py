
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    channel: str = Field(min_length=2, max_length=50)
    language: str = Field(default="English", max_length=50)
    subject: str | None = Field(default=None, max_length=255)
    body: str = Field(min_length=1)


class TemplateResponse(BaseModel):
    id: int
    name: str
    channel: str
    language: str
    subject: str | None = None
    body: str
    created_by: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
