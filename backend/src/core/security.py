import uuid
from datetime import datetime, timedelta, timezone

from aegra_api.core.orm import get_session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.settings import settings
from src.models.user import User
from src.schemas.auth import TokenPayload
from src.schemas.user import UserRead

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def create_access_token(user_id: uuid.UUID) -> str:
    """Create a signed JWT access token for the given user.

    The payload stores the user_id under the standard 'sub' (subject) claim
    and includes a 'type' claim so decode_token can reject refresh tokens
    when an access token is required.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(  # type: ignore[no-any-return]
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    """Create a signed JWT refresh token for the given user.

    Refresh tokens have a longer lifetime than access tokens and are only
    accepted by the /auth/refresh endpoint — never by protected API routes.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(  # type: ignore[no-any-return]
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_token(token: str, expected_type: str = "access") -> TokenPayload:
    """Decode and validate a JWT, returning its payload.

    Raises HTTPException 401 if:
    - The token signature is invalid.
    - The token has expired.
    - The token is malformed (missing required claims).
    - The 'type' claim does not match expected_type (prevents a refresh token
      from being used as an access token and vice-versa).
    """
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        data = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        payload = TokenPayload(**data)
    except (JWTError, ValidationError):
        raise credentials_error

    # Prevent cross-token misuse: a refresh token must not work as access, and
    # an access token must not work as refresh.
    if payload.type != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    """FastAPI dependency that validates the Bearer token and returns the
    authenticated user as a UserRead.

    Raises 401 if the token is invalid, expired, of the wrong type, or if
    the user stored in the token no longer exists in the database.
    This dependency is injected into every protected endpoint.
    """
    payload = decode_token(token, expected_type="access")

    result = await session.execute(
        select(User).where(User.id == uuid.UUID(payload.sub))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserRead.model_validate(user)


async def get_current_admin(
    current_user: UserRead = Depends(get_current_user),
) -> UserRead:
    """FastAPI dependency that extends get_current_user with an admin check.

    Raises 403 (Forbidden) if the authenticated user does not have is_admin=True.
    Used as a dependency on routes that only admins should access, such as
    activating/deactivating accounts or deleting users.

    Note: 403 (not 401) is correct here — the user is authenticated but lacks
    the required permission.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
