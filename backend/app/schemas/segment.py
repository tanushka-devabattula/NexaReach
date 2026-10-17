
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SegmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    description: str | None = None
    criteria: dict[str, Any] = Field(default_factory=dict)


class SegmentResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    criteria: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
