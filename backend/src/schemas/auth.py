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


class TokenPair(BaseModel):
    """Internal: a fresh access + refresh token pair issued by AuthService.

    Routes split this so the access token goes in the JSON body and the
    refresh token is set as an HttpOnly cookie — never returned to JavaScript.
    """

    access_token: str
    refresh_token: str
    expires_in: int  # seconds until the access_token expires


class AccessTokenResponse(BaseModel):
    """Public response after login/refresh.

    The refresh token is intentionally absent: it is delivered as an
    HttpOnly; Secure; SameSite=Lax cookie scoped to /api/v1/auth, so JS
    code (and any successful XSS) cannot read it.
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: str  # user_id as string
    exp: datetime
    type: Literal["access", "refresh"]
    jti: str | None = None  # only set on refresh tokens; rotated on every use
