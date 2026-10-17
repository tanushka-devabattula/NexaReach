
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20)
    organization: str | None = Field(default=None, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="user", pattern="^user$")


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: str | None = None
    organization: str | None = None
    role_id: int | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
