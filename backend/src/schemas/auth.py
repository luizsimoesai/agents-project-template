from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, field_validator

_MIN_PASSWORD_LEN = 8


# LoginRequest is the body for POST /auth/login.
# Uses EmailStr so Pydantic validates the format before we even touch the database.
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < _MIN_PASSWORD_LEN:
            raise ValueError("password must be at least 8 characters")
        return v


# TokenResponse is returned after a successful login or token refresh.
# expires_in tells the client how many seconds until the access_token expires
# so it can schedule a refresh proactively instead of waiting for a 401.
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until the access_token expires


# TokenPayload represents the claims decoded from a JWT.
# sub holds the user_id as a string (JWT standard uses strings for subjects).
# type distinguishes access tokens from refresh tokens so a refresh token
# cannot be used as an access token and vice-versa.
class TokenPayload(BaseModel):
    sub: str  # user_id as string
    exp: datetime
    type: Literal["access", "refresh"]


# RefreshRequest is the body for POST /auth/refresh.
class RefreshRequest(BaseModel):
    refresh_token: str
