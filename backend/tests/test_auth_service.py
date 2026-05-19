import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import bcrypt
import pytest
from fastapi import HTTPException
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import decode_token
from src.core.settings import settings
from src.schemas.auth import LoginRequest, PasswordChangeRequest, TokenPair
from src.services.auth_service import AuthService

_HTTP_400 = 400
_HTTP_401 = 401


def _make_execute_result(user):
    """Return a mock that simulates session.execute(...).scalar_one_or_none()."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    return mock_result


# ---------------------------------------------------------------------------
# login — success
# ---------------------------------------------------------------------------


async def test_login_success_returns_token_response(mock_session, user_factory):
    """Valid credentials return a TokenPair with non-empty tokens."""
    user = user_factory()
    mock_session.execute.return_value = _make_execute_result(user)

    service = AuthService(mock_session)
    data = LoginRequest(email=user.email, password="password123")
    result = await service.login(data)

    assert isinstance(result, TokenPair)
    assert result.access_token
    assert result.refresh_token
    assert result.expires_in > 0


# ---------------------------------------------------------------------------
# login — email doesn't exist
# ---------------------------------------------------------------------------


async def test_login_unknown_email_raises_401(mock_session):
    """When the user is not found, login raises 401 with 'Invalid credentials'."""
    mock_session.execute.return_value = _make_execute_result(None)

    service = AuthService(mock_session)
    data = LoginRequest(email="nobody@example.com", password="password123")

    with pytest.raises(HTTPException) as exc_info:
        await service.login(data)

    assert exc_info.value.status_code == _HTTP_401
    assert exc_info.value.detail == "Invalid credentials"


# ---------------------------------------------------------------------------
# login — wrong password
# ---------------------------------------------------------------------------


async def test_login_wrong_password_raises_401(mock_session, user_factory):
    """Wrong password raises 401 with 'Invalid credentials'."""
    user = user_factory()
    mock_session.execute.return_value = _make_execute_result(user)

    service = AuthService(mock_session)
    data = LoginRequest(email=user.email, password="wrongpass")

    with pytest.raises(HTTPException) as exc_info:
        await service.login(data)

    assert exc_info.value.status_code == _HTTP_401
    assert exc_info.value.detail == "Invalid credentials"


# ---------------------------------------------------------------------------
# login — inactive user
# ---------------------------------------------------------------------------


async def test_login_inactive_user_raises_401(mock_session, user_factory):
    """An inactive user gets 401 even with correct credentials."""
    user = user_factory(is_active=False)
    mock_session.execute.return_value = _make_execute_result(user)

    service = AuthService(mock_session)
    data = LoginRequest(email=user.email, password="password123")

    with pytest.raises(HTTPException) as exc_info:
        await service.login(data)

    assert exc_info.value.status_code == _HTTP_401
    assert exc_info.value.detail == "Invalid credentials"


# ---------------------------------------------------------------------------
# login — timing-safe: _verify_password called even when user is None
# ---------------------------------------------------------------------------


async def test_login_verify_password_called_when_user_not_found(mock_session):
    """_verify_password is always called (timing-safe), even when user is None."""
    mock_session.execute.return_value = _make_execute_result(None)

    patch_target = "src.services.auth_service._verify_password"
    with patch(patch_target, return_value=False) as mock_verify:
        service = AuthService(mock_session)
        data = LoginRequest(email="ghost@example.com", password="password123")

        with pytest.raises(HTTPException):
            await service.login(data)

        mock_verify.assert_called_once()
        # The dummy hash (not the user's hash) should have been passed
        call_args = mock_verify.call_args
        assert call_args[0][0] == "password123"
        # The hash passed is the static dummy hash used for timing safety
        assert call_args[0][1].startswith("$2b$12$")


# ---------------------------------------------------------------------------
# refresh — valid refresh token returns new TokenPair
# ---------------------------------------------------------------------------


async def test_refresh_valid_token_returns_new_token_pair(
    mock_session, user_factory, make_token
):
    """A valid refresh token (jti matches stored) returns a new TokenPair."""
    user = user_factory()
    user.refresh_jti = "stored-jti"
    refresh_token = make_token(user.id, type="refresh", jti="stored-jti")
    mock_session.execute.return_value = _make_execute_result(user)

    service = AuthService(mock_session)
    result = await service.refresh(refresh_token)

    assert isinstance(result, TokenPair)
    assert result.access_token
    assert result.refresh_token
    # The user's jti was rotated to a new value.
    assert user.refresh_jti is not None
    assert user.refresh_jti != "stored-jti"
    # New access token decodes with correct sub and type
    payload = decode_token(result.access_token, expected_type="access")
    assert uuid.UUID(payload.sub) == user.id


async def test_refresh_stale_jti_invalidates_session(
    mock_session, user_factory, make_token
):
    """A refresh whose jti doesn't match the stored one is rejected AND clears
    the stored jti — forcing the legitimate user to re-authenticate."""
    user = user_factory()
    user.refresh_jti = "current-jti"
    stolen_token = make_token(user.id, type="refresh", jti="stolen-old-jti")
    mock_session.execute.return_value = _make_execute_result(user)

    service = AuthService(mock_session)
    with pytest.raises(HTTPException) as exc_info:
        await service.refresh(stolen_token)

    assert exc_info.value.status_code == _HTTP_401
    assert user.refresh_jti is None  # whole session invalidated


async def test_refresh_missing_jti_rejected(mock_session, user_factory):
    """A legacy refresh token (no jti claim) is rejected after migration."""
    user = user_factory()
    user.refresh_jti = "current-jti"

    legacy_payload = {
        "sub": str(user.id),
        "type": "refresh",
        "exp": datetime.now(UTC) + timedelta(days=1),
    }
    legacy_token = jwt.encode(
        legacy_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    mock_session.execute.return_value = _make_execute_result(user)

    service = AuthService(mock_session)
    with pytest.raises(HTTPException) as exc_info:
        await service.refresh(legacy_token)
    assert exc_info.value.status_code == _HTTP_401


async def test_refresh_inactive_user_rejected(
    mock_session, user_factory, make_token
):
    """An inactive user's refresh token is rejected even with matching jti."""
    user = user_factory(is_active=False)
    user.refresh_jti = "stored-jti"
    refresh_token = make_token(user.id, type="refresh", jti="stored-jti")
    mock_session.execute.return_value = _make_execute_result(user)

    service = AuthService(mock_session)
    with pytest.raises(HTTPException) as exc_info:
        await service.refresh(refresh_token)
    assert exc_info.value.status_code == _HTTP_401


async def test_refresh_missing_user_rejected(mock_session, make_token):
    """A refresh whose sub points to a deleted user is rejected."""
    refresh_token = make_token(uuid.uuid4(), type="refresh", jti="x")
    mock_session.execute.return_value = _make_execute_result(None)

    service = AuthService(mock_session)
    with pytest.raises(HTTPException) as exc_info:
        await service.refresh(refresh_token)
    assert exc_info.value.status_code == _HTTP_401


# ---------------------------------------------------------------------------
# refresh — access token used as refresh raises 401
# ---------------------------------------------------------------------------


async def test_refresh_with_access_token_raises_401(make_token):
    """Passing an access token to refresh() raises 401 (wrong token type).

    decode_token rejects this before we ever query the DB.
    """
    user_id = uuid.uuid4()
    access_token = make_token(user_id, type="access")

    session = AsyncMock(spec=AsyncSession)
    service = AuthService(session)

    with pytest.raises(HTTPException) as exc_info:
        await service.refresh(access_token)

    assert exc_info.value.status_code == _HTTP_401


# ---------------------------------------------------------------------------
# refresh — expired token raises 401
# ---------------------------------------------------------------------------


async def test_refresh_expired_token_raises_401():
    """An expired refresh token raises 401 (rejected by decode_token)."""
    user_id = uuid.uuid4()
    expired_payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.now(UTC) - timedelta(seconds=1),
        "jti": "irrelevant",
    }
    expired_token = jwt.encode(
        expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    session = AsyncMock(spec=AsyncSession)
    service = AuthService(session)

    with pytest.raises(HTTPException) as exc_info:
        await service.refresh(expired_token)

    assert exc_info.value.status_code == _HTTP_401


# ---------------------------------------------------------------------------
# change_password
# ---------------------------------------------------------------------------


class TestChangePassword:
    """Service-level tests for AuthService.change_password.

    Covers the happy path (rehash + jti cleared), wrong current password
    (raises 400, no state changes), and new == current rejection.
    """

    async def test_success_updates_hash_and_clears_refresh_jti(
        self, mock_session, user_factory
    ):
        user = user_factory()
        user.refresh_jti = "active-jti"
        original_hash = user.password_hash
        mock_session.execute.return_value = _make_execute_result(user)

        service = AuthService(mock_session)
        data = PasswordChangeRequest(
            current_password="password123",
            new_password="brand-new-password",
        )
        await service.change_password(user.id, data)

        # password_hash was rotated (different bytes, verifies against the new
        # password — not the old one).
        assert user.password_hash != original_hash
        assert bcrypt.checkpw(b"brand-new-password", user.password_hash.encode())
        assert not bcrypt.checkpw(b"password123", user.password_hash.encode())
        # All refresh sessions invalidated.
        assert user.refresh_jti is None
        mock_session.commit.assert_awaited()

    async def test_wrong_current_password_raises_400(
        self, mock_session, user_factory
    ):
        user = user_factory()
        user.refresh_jti = "active-jti"
        original_hash = user.password_hash
        mock_session.execute.return_value = _make_execute_result(user)

        service = AuthService(mock_session)
        data = PasswordChangeRequest(
            current_password="wrong-current",
            new_password="brand-new-password",
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.change_password(user.id, data)

        assert exc_info.value.status_code == _HTTP_400
        assert exc_info.value.detail == "Current password is incorrect"
        # No mutation occurred.
        assert user.password_hash == original_hash
        assert user.refresh_jti == "active-jti"
        mock_session.commit.assert_not_awaited()

    async def test_new_equals_current_raises_400(self, mock_session, user_factory):
        user = user_factory()
        user.refresh_jti = "active-jti"
        original_hash = user.password_hash
        mock_session.execute.return_value = _make_execute_result(user)

        service = AuthService(mock_session)
        # Both current and new are the seeded password.
        data = PasswordChangeRequest(
            current_password="password123",
            new_password="password123",
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.change_password(user.id, data)

        _msg = "New password must be different from current password"
        assert exc_info.value.status_code == _HTTP_400
        assert exc_info.value.detail == _msg
        assert user.password_hash == original_hash
        assert user.refresh_jti == "active-jti"
        mock_session.commit.assert_not_awaited()
