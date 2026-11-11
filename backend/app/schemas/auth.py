from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# Roles a person may ask for when registering. "admin" can never be self-assigned.
REGISTRABLE_ROLES = ("user", "campaign_manager", "communication_team")


class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20)
    organization: str | None = Field(default=None, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="user", description="user, campaign_manager or communication_team")

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, value: str) -> str:
        problems = []
        if not any(c.islower() for c in value):
            problems.append("a lowercase letter")
        if not any(c.isupper() for c in value):
            problems.append("an uppercase letter")
        if not any(c.isdigit() for c in value):
            problems.append("a number")
        if problems:
            raise ValueError("Password must contain " + ", ".join(problems) + ".")
        return value

    @field_validator("role")
    @classmethod
    def role_must_be_allowed(cls, value: str) -> str:
        clean = value.strip().lower()
        if clean not in REGISTRABLE_ROLES:
            raise ValueError("Role must be one of: " + ", ".join(REGISTRABLE_ROLES) + ".")
        return clean


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: str | None = None
    organization: str | None = None
    role_id: int | None = None
    role: str | None = None
    is_active: bool
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RoleChange(BaseModel):
    role: str


class ActiveChange(BaseModel):
    is_active: bool
