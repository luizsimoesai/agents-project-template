# backend/tests/test_auth_handler.py
import uuid
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from unittest.mock import patch

import pytest
from jose import jwt
from langgraph_sdk import Auth

from src.auth.jwt import authenticate
from src.core.security import create_access_token, create_refresh_token
from src.core.settings import settings

HTTP_401 = HTTPStatus.UNAUTHORIZED.value


def _patch_fetch_active_user(user_or_none):
    """Mock src.auth.jwt._fetch_active_user to return the given user (or None)."""

    async def _fake(_user_id: str):
        return user_or_none

    return patch("src.auth.jwt._fetch_active_user", side_effect=_fake)


async def test_valid_access_token(user_factory):
    user = user_factory()
    token = create_access_token(user.id)
    with _patch_fetch_active_user(user):
        result = await authenticate({"authorization": f"Bearer {token}"})
    assert result["identity"] == str(user.id)
    assert "authenticated" in result["permissions"]
    assert "admin" not in result["permissions"]


async def test_admin_gets_admin_permission(user_factory):
    admin = user_factory(is_admin=True)
    token = create_access_token(admin.id)
    with _patch_fetch_active_user(admin):
        result = await authenticate({"authorization": f"Bearer {token}"})
    assert "admin" in result["permissions"]


async def test_inactive_user_rejected(user_factory):
    """A deactivated user's still-valid access token is rejected at the
    Aegra layer — otherwise they'd keep calling /threads/etc until expiry."""
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    # simulates inactive or missing user
    with (
        _patch_fetch_active_user(None),
        pytest.raises(Auth.exceptions.HTTPException) as exc_info,
    ):
        await authenticate({"authorization": f"Bearer {token}"})
    assert exc_info.value.status_code == HTTP_401


async def test_missing_authorization_header():
    with pytest.raises(Auth.exceptions.HTTPException) as exc_info:
        await authenticate({})
    assert exc_info.value.status_code == HTTP_401


async def test_empty_token_after_bearer():
    with pytest.raises(Auth.exceptions.HTTPException) as exc_info:
        await authenticate({"authorization": "Bearer "})
    assert exc_info.value.status_code == HTTP_401


async def test_invalid_signature_tampered_token():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    tampered = token[:-4] + "XXXX"
    with pytest.raises(Auth.exceptions.HTTPException) as exc_info:
        await authenticate({"authorization": f"Bearer {tampered}"})
    assert exc_info.value.status_code == HTTP_401


async def test_expired_token():
    user_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.now(UTC) - timedelta(minutes=5),
    }
    expired_token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    with pytest.raises(Auth.exceptions.HTTPException) as exc_info:
        await authenticate({"authorization": f"Bearer {expired_token}"})
    assert exc_info.value.status_code == HTTP_401


async def test_refresh_token_rejected():
    user_id = uuid.uuid4()
    token = create_refresh_token(user_id, jti="some-jti")
    with pytest.raises(Auth.exceptions.HTTPException) as exc_info:
        await authenticate({"authorization": f"Bearer {token}"})
    assert exc_info.value.status_code == HTTP_401


async def test_lowercase_authorization_header_key(user_factory):
    user = user_factory()
    token = create_access_token(user.id)
    with _patch_fetch_active_user(user):
        result = await authenticate({"authorization": f"Bearer {token}"})
    assert result["identity"] == str(user.id)


async def test_token_missing_subject_claim():
    """Token with empty sub claim raises 401."""
    payload = {
        "sub": "",  # empty sub triggers the guard
        "type": "access",
        "exp": datetime.now(UTC) + timedelta(minutes=30),
    }
    no_sub_token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    with pytest.raises(Auth.exceptions.HTTPException) as exc_info:
        await authenticate({"authorization": f"Bearer {no_sub_token}"})
    assert exc_info.value.status_code == HTTP_401
