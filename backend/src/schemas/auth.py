from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, field_validator

_MIN_PASSWORD_LEN = 8


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < _MIN_PASSWORD_LEN:
            raise ValueError("password must be at least 8 characters")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until the access_token expires


class TokenPayload(BaseModel):
    sub: str  # user_id as string
    exp: datetime
    type: Literal["access", "refresh"]


class RefreshRequest(BaseModel):
    refresh_token: str
