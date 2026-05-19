import secrets
import uuid

import bcrypt
from aegra_api.core.orm import get_session
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import (
    _BCRYPT_ROUNDS,
    _hash_password,
    _verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from src.core.settings import settings
from src.models.user import User
from src.schemas.auth import LoginRequest, PasswordChangeRequest, TokenPair
from src.services.user_service import UserService

# Generated once at import to keep timing-attack mitigation correct.
# Must use the same cost factor as real password hashing — otherwise the
# response time differs between "email exists" and "email missing" and the
# mitigation is defeated. A hand-written constant string cannot be trusted:
# bcrypt versions vary in what they accept and an invalid hash would raise
# ValueError, turning the login path into an existence oracle.
_DUMMY_PASSWORD_HASH = bcrypt.hashpw(
    b"x", bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
).decode()


class AuthService:
    """Handles authentication flows: login and token refresh.

    Depends on UserService internally to look up users by email.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._user_service = UserService(session)

    async def login(self, data: LoginRequest) -> TokenPair:
        """Validate credentials and issue a new token pair.

        Security note: we always return the same error message regardless of
        whether the email doesn't exist or the password is wrong.  Giving
        different messages would let an attacker enumerate valid email addresses.
        """
        user = await self._user_service.get_user_by_email(data.email)

        # Constant-time comparison: pwd_context.verify avoids timing attacks.
        # We still call verify even when user is None (using a dummy hash) so the
        # response time does not reveal whether the email exists.
        password_hash = (
            user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
        )
        valid = _verify_password(data.password, password_hash)

        if user is None or not valid or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        jti = secrets.token_urlsafe(16)
        user.refresh_jti = jti
        await self.session.commit()

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id, jti=jti)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def refresh(self, refresh_token: str) -> TokenPair:
        """Validate a refresh token and rotate it.

        Each refresh token embeds a jti claim that must match the user's
        stored refresh_jti. Presenting a stale jti — whether due to a
        legitimate-but-out-of-order request or a replay attack with a stolen
        token — is rejected and treated as a session compromise: refresh_jti
        is cleared so even the legitimate session must log in again.
        """
        payload = decode_token(refresh_token, expected_type="refresh")
        user_id = uuid.UUID(payload.sub)

        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        unauthorized = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

        if user is None or not user.is_active:
            raise unauthorized

        # Reject refresh tokens minted before jti was introduced (jti=None) or
        # whose jti doesn't match the current stored one.
        if payload.jti is None or user.refresh_jti != payload.jti:
            # Replay or stale token: invalidate the entire session so the
            # legitimate user is forced to re-authenticate.
            user.refresh_jti = None
            await self.session.commit()
            raise unauthorized

        new_jti = secrets.token_urlsafe(16)
        user.refresh_jti = new_jti
        await self.session.commit()

        new_access = create_access_token(user_id)
        new_refresh = create_refresh_token(user_id, jti=new_jti)

        return TokenPair(
            access_token=new_access,
            refresh_token=new_refresh,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def change_password(
        self, user_id: uuid.UUID, data: PasswordChangeRequest
    ) -> None:
        """Verify current password, rehash the new one, invalidate all sessions.

        Side effects on success:
          * users.password_hash is rotated to bcrypt(new_password).
          * users.refresh_jti is cleared — every active refresh token across
            every device is invalidated. The route is responsible for also
            clearing the refresh cookie on the current response.

        Raises:
            HTTPException 401: user not found or inactive (defensive — the
                route's get_current_user dependency already filters these
                cases, but the service revalidates so it stays safe to call
                from other entry points).
            HTTPException 400: current_password does not match, OR
                new_password equals the current password.
        """
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not _verify_password(data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        if data.new_password == data.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password",
            )

        user.password_hash = _hash_password(data.new_password)
        user.refresh_jti = None
        await self.session.commit()

    async def logout(self, refresh_token: str | None) -> None:
        """Best-effort server-side invalidation of the refresh token.

        Clears the user's refresh_jti so any further /auth/refresh with this
        token is rejected. Silently does nothing if the token is missing,
        invalid, or expired — the cookie is cleared by the route regardless.
        """
        if not refresh_token:
            return
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
        except HTTPException:
            return

        result = await self.session.execute(
            select(User).where(User.id == uuid.UUID(payload.sub))
        )
        user = result.scalar_one_or_none()
        if user is None:
            return
        user.refresh_jti = None
        await self.session.commit()


def get_auth_service(
    session: AsyncSession = Depends(get_session),
) -> AuthService:
    """FastAPI dependency factory for AuthService.

    Follows the same Aegra pattern as get_user_service.
    """
    return AuthService(session)
