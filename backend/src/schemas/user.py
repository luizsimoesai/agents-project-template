import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

_MIN_PASSWORD_LEN = 8


# UserCreate is the request body for creating a new user.
# The password is accepted in plain text here and hashed by the service layer —
# it is never stored as-is and never returned in any response.
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


# UserRead is the public representation of a user.
# It deliberately omits password_hash so sensitive data never leaks to clients.
# from_attributes=True lets Pydantic read values from SQLAlchemy ORM instances
# directly (e.g. UserRead.model_validate(orm_user)).
# is_admin and is_active are included so clients (and security dependencies like
# get_current_admin) can read these flags without an extra database round-trip.
class UserRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str | None
    email: str
    is_admin: bool
    is_active: bool
    created_at: datetime


# UserUpdate carries optional fields for PATCH semantics:
# only the fields that are explicitly sent by the client will be updated.
class UserUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
