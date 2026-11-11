from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.services.audience_service import (
    CHANNELS,
    GENDERS,
    LANGUAGES,
    canonical_phone,
    pick_from,
)

_OPTIONAL_TEXT = ("email", "phone", "age", "gender", "city", "state", "occupation", "department",
                  "preferred_channel")


def _strip_blank(value: Any) -> Any:
    """'  ' -> None, ' Hyderabad ' -> 'Hyderabad'. Other types are left alone."""
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class AudienceCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    age: Optional[int] = Field(default=None, ge=0, le=120)
    gender: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    occupation: Optional[str] = Field(default=None, max_length=100)
    department: Optional[str] = Field(default=None, max_length=150)
    preferred_language: str = Field(default="English", max_length=50)
    preferred_channel: Optional[str] = None
    consent: bool = False

    @field_validator("full_name", mode="before")
    @classmethod
    def _name(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator(*_OPTIONAL_TEXT, mode="before")
    @classmethod
    def _blank(cls, v):
        return _strip_blank(v)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v):
        return canonical_phone(v)

    @field_validator("gender")
    @classmethod
    def _gender(cls, v):
        return pick_from(v, GENDERS, "gender")

    @field_validator("preferred_channel")
    @classmethod
    def _channel(cls, v):
        return pick_from(v, CHANNELS, "channel")

    @field_validator("preferred_language", mode="before")
    @classmethod
    def _language(cls, v):
        return pick_from(v, LANGUAGES, "language") or "English"

    @model_validator(mode="after")
    def _needs_a_contact(self):
        if not self.email and not self.phone:
            raise ValueError("Provide at least an email or a phone number")
        return self


class AudienceUpdate(BaseModel):
    """PATCH body: send only what changes. Sending null clears an optional field."""
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    age: Optional[int] = Field(default=None, ge=0, le=120)
    gender: Optional[str] = None
    city: Optional[str] = Field(default=None, max_length=100)
    state: Optional[str] = Field(default=None, max_length=100)
    occupation: Optional[str] = Field(default=None, max_length=100)
    department: Optional[str] = Field(default=None, max_length=150)
    preferred_language: Optional[str] = Field(default=None, max_length=50)
    preferred_channel: Optional[str] = None
    consent: Optional[bool] = None

    @field_validator("full_name", mode="before")
    @classmethod
    def _name(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator(*_OPTIONAL_TEXT, mode="before")
    @classmethod
    def _blank(cls, v):
        return _strip_blank(v)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v):
        return canonical_phone(v)

    @field_validator("gender")
    @classmethod
    def _gender(cls, v):
        return pick_from(v, GENDERS, "gender")

    @field_validator("preferred_channel")
    @classmethod
    def _channel(cls, v):
        return pick_from(v, CHANNELS, "channel")

    @field_validator("preferred_language", mode="before")
    @classmethod
    def _language(cls, v):
        return pick_from(v, LANGUAGES, "language")


class AudienceResponse(BaseModel):
    id: int
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    occupation: Optional[str] = None
    department: Optional[str] = None
    preferred_language: str
    preferred_channel: Optional[str] = None
    consent: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AudiencePage(BaseModel):
    items: List[AudienceResponse]
    total: int
    page: int
    page_size: int
    pages: int


class BulkRowError(BaseModel):
    row: int
    name: Optional[str] = None
    reason: str


class BulkUploadResult(BaseModel):
    total_rows: int
    added: int
    failed: int
    errors: List[BulkRowError]
