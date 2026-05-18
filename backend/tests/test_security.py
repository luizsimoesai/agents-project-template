# backend/tests/test_security.py
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, status
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_admin,
    get_current_user,
)
from src.core.settings import settings
from src.schemas.user import UserRead

# ── Token creation ──────────────────────────────────────────────────────────


def test_create_access_token_claims():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    data = jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    assert data["sub"] == str(user_id)
    assert data["type"] == "access"
    assert data["exp"] > datetime.now(UTC).timestamp()


def test_create_refresh_token_claims():
    user_id = uuid.uuid4()
    token = create_refresh_token(user_id, jti="some-jti")
    data = jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    assert data["sub"] == str(user_id)
    assert data["type"] == "refresh"
    assert data["jti"] == "some-jti"
    # refresh token lifetime must be longer than access token lifetime
    access = create_access_token(user_id)
    access_data = jwt.decode(
        access, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )
    assert data["exp"] > access_data["exp"]


# ── decode_token ─────────────────────────────────────────────────────────────


def test_decode_token_valid_access():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    payload = decode_token(token, expected_type="access")
    assert payload.sub == str(user_id)
    assert payload.type == "access"


def test_decode_token_wrong_type_raises_401():
    user_id = uuid.uuid4()
    access_token = create_access_token(user_id)
    with pytest.raises(HTTPException) as exc_info:
        decode_token(access_token, expected_type="refresh")
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_decode_token_invalid_signature_raises_401():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    tampered = token[:-4] + "XXXX"
    with pytest.raises(HTTPException) as exc_info:
        decode_token(tampered)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_decode_token_expired_raises_401():
    user_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.now(UTC) - timedelta(minutes=5),
    }
    expired_token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_token(expired_token)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


# ── get_current_user ─────────────────────────────────────────────────────────


async def test_get_current_user_valid_token(user_factory):
    user = user_factory()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.return_value = mock_result

    token = create_access_token(user.id)
    result = await get_current_user(token=token, session=mock_session)

    assert result.id == user.id
    assert result.email == user.email
    assert not hasattr(result, "password_hash")


async def test_get_current_user_not_found_raises_401(user_factory):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.return_value = mock_result

    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=token, session=mock_session)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


async def test_get_current_user_inactive_raises_401(user_factory):
    user = user_factory(is_active=False)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.return_value = mock_result

    token = create_access_token(user.id)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=token, session=mock_session)
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


# ── get_current_admin ────────────────────────────────────────────────────────


async def test_get_current_admin_passes_for_admin(user_factory):
    admin = user_factory(is_admin=True)
    user_read = UserRead.model_validate(admin)
    result = await get_current_admin(current_user=user_read)
    assert result.is_admin is True


async def test_get_current_admin_raises_403_for_non_admin(user_factory):
    user = user_factory(is_admin=False)
    user_read = UserRead.model_validate(user)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(current_user=user_read)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
