
from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict, Field


class AudienceCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20)
    preferred_language: str = Field(default="English", max_length=50)


class AudienceResponse(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str | None = None
    preferred_language: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
