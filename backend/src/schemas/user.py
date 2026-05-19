import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

_MIN_PASSWORD_LEN = 8


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < _MIN_PASSWORD_LEN:
            raise ValueError("password must be at least 8 characters")
        return v


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str | None
    email: str
    is_admin: bool
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
