"""Integration tests for the /api/v1/auth routes.

All DB dependencies are replaced with AsyncMock so no PostgreSQL connection
is required.  The test_app fixture (from conftest.py) resets
dependency_overrides before and after each test.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

from src.core.security import get_current_user
from src.schemas.auth import TokenResponse
from src.schemas.user import UserRead
from src.services.auth_service import AuthService, get_auth_service
from src.services.user_service import UserService, get_user_service

# ---------------------------------------------------------------------------
# HTTP status code constants (avoids PLR2004 magic-number warnings)
# ---------------------------------------------------------------------------

_HTTP_200 = 200
_HTTP_201 = 201
_HTTP_401 = 401
_HTTP_409 = 409
_HTTP_422 = 422

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXPIRES_IN = 1800  # arbitrary; used to build TokenResponse mocks


def _make_user_read(**kwargs) -> UserRead:
    return UserRead(
        id=kwargs.get("id", uuid.uuid4()),
        name=kwargs.get("name", "Test User"),
        email=kwargs.get("email", "test@example.com"),
        is_admin=kwargs.get("is_admin", False),
        is_active=kwargs.get("is_active", True),
        created_at=kwargs.get(
            "created_at", datetime(2024, 1, 1, tzinfo=timezone.utc)
        ),
    )


def _make_token_response(**kwargs) -> TokenResponse:
    return TokenResponse(
        access_token=kwargs.get("access_token", "access.token.value"),
        refresh_token=kwargs.get("refresh_token", "refresh.token.value"),
        token_type="bearer",
        expires_in=kwargs.get("expires_in", _EXPIRES_IN),
    )


def _async_client(app) -> httpx.AsyncClient:
    """Return an AsyncClient wired to the given ASGI app."""
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# Shared fixture: mocked services + async HTTP client
# ---------------------------------------------------------------------------


@pytest.fixture
async def auth_client(test_app):
    """Yields (client, mock_user_svc, mock_auth_svc) with overrides applied."""
    mock_user_svc = AsyncMock(spec=UserService)
    mock_auth_svc = AsyncMock(spec=AuthService)

    test_app.dependency_overrides[get_user_service] = lambda: mock_user_svc
    test_app.dependency_overrides[get_auth_service] = lambda: mock_auth_svc

    async with _async_client(test_app) as client:
        yield client, mock_user_svc, mock_auth_svc


# ---------------------------------------------------------------------------
# POST /api/v1/auth/register
# ---------------------------------------------------------------------------


class TestRegister:
    async def test_register_valid(self, auth_client):
        client, mock_user_svc, _ = auth_client
        user = _make_user_read(email="new@example.com")
        mock_user_svc.create_user.return_value = user

        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "New User",
                "email": "new@example.com",
                "password": "securepass",
            },
        )

        assert resp.status_code == _HTTP_201
        body = resp.json()
        assert body["email"] == "new@example.com"
        assert "password_hash" not in body
        assert "password" not in body

    async def test_register_duplicate_email(self, auth_client):
        client, mock_user_svc, _ = auth_client
        mock_user_svc.create_user.side_effect = HTTPException(
            status_code=_HTTP_409,
            detail="A user with this email already exists",
        )

        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "name": "Dup User",
                "email": "dup@example.com",
                "password": "securepass",
            },
        )

        assert resp.status_code == _HTTP_409
        assert "already exists" in resp.json()["detail"]

    async def test_register_short_password(self, auth_client):
        client, _, _ = auth_client

        resp = await client.post(
            "/api/v1/auth/register",
            json={"name": "User", "email": "user@example.com", "password": "short"},
        )

        assert resp.status_code == _HTTP_422


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------


class TestLogin:
    async def test_login_valid_credentials(self, auth_client):
        client, _, mock_auth_svc = auth_client
        token_resp = _make_token_response(
            access_token="good.access.token",
            refresh_token="good.refresh.token",
        )
        mock_auth_svc.login.return_value = token_resp

        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )

        assert resp.status_code == _HTTP_200
        body = resp.json()
        assert body["access_token"] == "good.access.token"
        assert body["refresh_token"] == "good.refresh.token"
        assert body["token_type"] == "bearer"

    async def test_login_wrong_password(self, auth_client):
        client, _, mock_auth_svc = auth_client
        mock_auth_svc.login.side_effect = HTTPException(
            status_code=_HTTP_401, detail="Invalid credentials"
        )

        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrongpass"},
        )

        assert resp.status_code == _HTTP_401
        assert resp.json()["detail"] == "Invalid credentials"

    async def test_login_inactive_user(self, auth_client):
        client, _, mock_auth_svc = auth_client
        mock_auth_svc.login.side_effect = HTTPException(
            status_code=_HTTP_401, detail="Invalid credentials"
        )

        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "inactive@example.com", "password": "password123"},
        )

        assert resp.status_code == _HTTP_401
        assert resp.json()["detail"] == "Invalid credentials"


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------


class TestMe:
    async def test_me_valid_token(self, test_app):
        """Override get_current_user directly so no JWT validation is needed."""
        user = _make_user_read(email="me@example.com")
        test_app.dependency_overrides[get_current_user] = lambda: user

        async with _async_client(test_app) as client:
            resp = await client.get("/api/v1/auth/me")

        assert resp.status_code == _HTTP_200
        assert resp.json()["email"] == "me@example.com"

    async def test_me_no_token(self, test_app):
        """No override — OAuth2PasswordBearer returns 401 when header is absent."""
        async with _async_client(test_app) as client:
            resp = await client.get("/api/v1/auth/me")

        assert resp.status_code == _HTTP_401


# ---------------------------------------------------------------------------
# POST /api/v1/auth/refresh
# ---------------------------------------------------------------------------


class TestRefresh:
    async def test_refresh_valid_token(self, auth_client):
        client, _, mock_auth_svc = auth_client
        token_resp = _make_token_response(
            access_token="new.access.token",
            refresh_token="new.refresh.token",
        )
        mock_auth_svc.refresh.return_value = token_resp

        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "valid.refresh.token"},
        )

        assert resp.status_code == _HTTP_200
        body = resp.json()
        assert "access_token" in body
        assert body["access_token"] == "new.access.token"

    async def test_refresh_with_access_token(self, auth_client):
        """Passing an access token where a refresh token is expected -> 401."""
        client, _, mock_auth_svc = auth_client
        mock_auth_svc.refresh.side_effect = HTTPException(
            status_code=_HTTP_401, detail="Invalid token type"
        )

        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "some.access.token"},
        )

        assert resp.status_code == _HTTP_401
