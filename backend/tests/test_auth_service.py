import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import decode_token
from src.core.settings import settings
from src.schemas.auth import LoginRequest, TokenResponse
from src.services.auth_service import AuthService

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
    """Valid credentials return a TokenResponse with non-empty tokens."""
    user = user_factory()
    mock_session.execute.return_value = _make_execute_result(user)

    service = AuthService(mock_session)
    data = LoginRequest(email=user.email, password="password123")
    result = await service.login(data)

    assert isinstance(result, TokenResponse)
    assert result.access_token
    assert result.refresh_token
    assert result.token_type == "bearer"
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
# refresh — valid refresh token returns new TokenResponse
# ---------------------------------------------------------------------------


async def test_refresh_valid_token_returns_new_token_pair(make_token):
    """A valid refresh token returns a new TokenResponse with a new access token."""
    user_id = uuid.uuid4()
    refresh_token = make_token(user_id, type="refresh")

    session = AsyncMock(spec=AsyncSession)
    service = AuthService(session)
    result = await service.refresh(refresh_token)

    assert isinstance(result, TokenResponse)
    assert result.access_token
    assert result.refresh_token
    assert result.token_type == "bearer"
    assert result.expires_in > 0
    # New access token decodes with correct sub and type
    payload = decode_token(result.access_token, expected_type="access")
    assert uuid.UUID(payload.sub) == user_id


# ---------------------------------------------------------------------------
# refresh — access token used as refresh raises 401
# ---------------------------------------------------------------------------


async def test_refresh_with_access_token_raises_401(make_token):
    """Passing an access token to refresh() raises 401 (wrong token type)."""
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
    """An expired refresh token raises 401."""
    user_id = uuid.uuid4()
    expired_payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
    }
    expired_token = jwt.encode(
        expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    session = AsyncMock(spec=AsyncSession)
    service = AuthService(session)

    with pytest.raises(HTTPException) as exc_info:
        await service.refresh(expired_token)

    assert exc_info.value.status_code == _HTTP_401
