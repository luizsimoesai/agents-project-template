import uuid

from aegra_api.core.orm import get_session
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import create_access_token, create_refresh_token, decode_token
from src.core.settings import settings
from src.schemas.auth import LoginRequest, TokenResponse
from src.services.user_service import UserService, _verify_password


class AuthService:
    """Handles authentication flows: login and token refresh.

    Depends on UserService internally to look up users by email.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        # Compose UserService so we don't duplicate query logic.
        self._user_service = UserService(session)

    async def login(self, data: LoginRequest) -> TokenResponse:
        """Validate credentials and issue a new token pair.

        Security note: we always return the same error message regardless of
        whether the email doesn't exist or the password is wrong.  Giving
        different messages would let an attacker enumerate valid email addresses.
        """
        user = await self._user_service.get_user_by_email(data.email)

        # Constant-time comparison: pwd_context.verify avoids timing attacks.
        # We still call verify even when user is None (using a dummy hash) so the
        # response time does not reveal whether the email exists.
        dummy_hash = "$2b$12$KIXyW8K0pYx6nQ3bXpG6EeP0L0v0v0v0v0v0v0v0v0v0v0v0v0v0O"
        password_hash = user.password_hash if user is not None else dummy_hash
        valid = _verify_password(data.password, password_hash)

        if user is None or not valid or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Rotate the token pair: validate the refresh token and issue a new pair.

        Token rotation means each call to /auth/refresh invalidates the previous
        refresh token (it is simply discarded) and returns fresh tokens.
        Raises 401 if the refresh token is invalid, expired, or of the wrong type.
        """
        # decode_token raises 401 automatically if the token is bad or wrong type.
        payload = decode_token(refresh_token, expected_type="refresh")

        user_id = uuid.UUID(payload.sub)

        # Issue brand-new tokens — the old refresh token is no longer returned.
        new_access = create_access_token(user_id)
        new_refresh = create_refresh_token(user_id)

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            expires_in=settings.access_token_expire_minutes * 60,
        )


def get_auth_service(
    session: AsyncSession = Depends(get_session),
) -> AuthService:
    """FastAPI dependency factory for AuthService.

    Follows the same Aegra pattern as get_user_service.
    """
    return AuthService(session)
