"""Integration tests for the /api/v1/auth routes.

All DB dependencies are replaced with AsyncMock so no PostgreSQL connection
is required.  The test_app fixture (from conftest.py) resets
dependency_overrides before and after each test.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

from src.core.security import get_current_user
from src.schemas.auth import TokenPair
from src.schemas.user import UserRead
from src.services.auth_service import AuthService, get_auth_service
from src.services.user_service import UserService, get_user_service

# ---------------------------------------------------------------------------
# HTTP status code constants (avoids PLR2004 magic-number warnings)
# ---------------------------------------------------------------------------

_HTTP_200 = 200
_HTTP_201 = 201
_HTTP_204 = 204
_HTTP_400 = 400
_HTTP_401 = 401
_HTTP_409 = 409
_HTTP_422 = 422

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXPIRES_IN = 1800  # arbitrary; used to build TokenPair mocks


def _make_user_read(**kwargs) -> UserRead:
    return UserRead(
        id=kwargs.get("id", uuid.uuid4()),
        name=kwargs.get("name", "Test User"),
        email=kwargs.get("email", "test@example.com"),
        is_admin=kwargs.get("is_admin", False),
        is_active=kwargs.get("is_active", True),
        created_at=kwargs.get("created_at", datetime(2024, 1, 1, tzinfo=UTC)),
    )


def _make_token_pair(**kwargs) -> TokenPair:
    return TokenPair(
        access_token=kwargs.get("access_token", "access.token.value"),
        refresh_token=kwargs.get("refresh_token", "refresh.token.value"),
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
        mock_auth_svc.login.return_value = _make_token_pair(
            access_token="good.access.token",
            refresh_token="good.refresh.token",
        )

        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )

        assert resp.status_code == _HTTP_200
        body = resp.json()
        # access token returned in body
        assert body["access_token"] == "good.access.token"
        assert body["token_type"] == "bearer"
        # refresh token is NOT in body — must be HttpOnly cookie
        assert "refresh_token" not in body
        # cookie is set, HttpOnly, scoped to /api/v1/auth
        set_cookie = resp.headers.get("set-cookie", "")
        assert "refresh_token=good.refresh.token" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Path=/api/v1/auth" in set_cookie

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
    async def test_refresh_valid_cookie(self, auth_client):
        client, _, mock_auth_svc = auth_client
        mock_auth_svc.refresh.return_value = _make_token_pair(
            access_token="new.access.token",
            refresh_token="new.refresh.token",
        )

        resp = await client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": "valid.refresh.token"},
        )

        assert resp.status_code == _HTTP_200
        body = resp.json()
        assert body["access_token"] == "new.access.token"
        assert "refresh_token" not in body
        # AuthService.refresh received the cookie value
        mock_auth_svc.refresh.assert_called_once_with("valid.refresh.token")
        # new refresh cookie was set
        assert "refresh_token=new.refresh.token" in resp.headers.get("set-cookie", "")

    async def test_refresh_missing_cookie_returns_401(self, auth_client):
        client, _, _ = auth_client
        resp = await client.post("/api/v1/auth/refresh")
        assert resp.status_code == _HTTP_401

    async def test_refresh_invalid_cookie_returns_401(self, auth_client):
        """If AuthService.refresh raises 401, the route propagates it."""
        client, _, mock_auth_svc = auth_client
        mock_auth_svc.refresh.side_effect = HTTPException(
            status_code=_HTTP_401, detail="Invalid token type"
        )

        resp = await client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": "bad.token"},
        )

        assert resp.status_code == _HTTP_401


class TestLogout:
    async def test_logout_clears_cookie(self, auth_client):
        client, _, mock_auth_svc = auth_client
        resp = await client.post(
            "/api/v1/auth/logout",
            cookies={"refresh_token": "some.token"},
        )
        assert resp.status_code == _HTTP_204
        mock_auth_svc.logout.assert_called_once_with("some.token")
        # Set-Cookie clears the cookie (expires in the past)
        set_cookie = resp.headers.get("set-cookie", "")
        assert "refresh_token=" in set_cookie
        assert "Path=/api/v1/auth" in set_cookie

    async def test_logout_without_cookie_is_idempotent(self, auth_client):
        client, _, mock_auth_svc = auth_client
        resp = await client.post("/api/v1/auth/logout")
        assert resp.status_code == _HTTP_204
        mock_auth_svc.logout.assert_called_once_with(None)


# ---------------------------------------------------------------------------
# POST /api/v1/auth/change-password
# ---------------------------------------------------------------------------


class TestChangePassword:
    async def test_success_returns_204_and_clears_cookie(self, test_app):
        """Happy path: 204, AuthService.change_password is called with the
        current user's id, and the refresh cookie is cleared in the response."""
        user = _make_user_read(email="me@example.com")
        test_app.dependency_overrides[get_current_user] = lambda: user

        mock_auth_svc = AsyncMock(spec=AuthService)
        test_app.dependency_overrides[get_auth_service] = lambda: mock_auth_svc

        async with _async_client(test_app) as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                headers={"Authorization": "Bearer dummy"},
                json={
                    "current_password": "password123",
                    "new_password": "brand-new-password",
                },
                cookies={"refresh_token": "old.refresh.token"},
            )

        assert resp.status_code == _HTTP_204
        # Service called once with user id + request body
        mock_auth_svc.change_password.assert_awaited_once()
        called_user_id, called_data = mock_auth_svc.change_password.await_args.args
        assert called_user_id == user.id
        assert called_data.current_password == "password123"
        assert called_data.new_password == "brand-new-password"
        # Refresh cookie cleared (Set-Cookie clears with Path=/api/v1/auth)
        set_cookie = resp.headers.get("set-cookie", "")
        assert "refresh_token=" in set_cookie
        assert "Path=/api/v1/auth" in set_cookie

    async def test_missing_bearer_returns_401(self, test_app):
        """OAuth2PasswordBearer returns 401 when the Authorization header
        is absent — no dependency override so the real dependency runs."""
        async with _async_client(test_app) as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                json={
                    "current_password": "password123",
                    "new_password": "brand-new-password",
                },
            )

        assert resp.status_code == _HTTP_401

    async def test_wrong_current_password_returns_400(self, test_app):
        user = _make_user_read()
        test_app.dependency_overrides[get_current_user] = lambda: user

        mock_auth_svc = AsyncMock(spec=AuthService)
        mock_auth_svc.change_password.side_effect = HTTPException(
            status_code=400, detail="Current password is incorrect"
        )
        test_app.dependency_overrides[get_auth_service] = lambda: mock_auth_svc

        async with _async_client(test_app) as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                headers={"Authorization": "Bearer dummy"},
                json={
                    "current_password": "wrong",
                    "new_password": "brand-new-password",
                },
            )

        assert resp.status_code == _HTTP_400
        assert resp.json()["detail"] == "Current password is incorrect"

    async def test_new_equals_current_returns_400(self, test_app):
        user = _make_user_read()
        test_app.dependency_overrides[get_current_user] = lambda: user

        mock_auth_svc = AsyncMock(spec=AuthService)
        mock_auth_svc.change_password.side_effect = HTTPException(
            status_code=400,
            detail="New password must be different from current password",
        )
        test_app.dependency_overrides[get_auth_service] = lambda: mock_auth_svc

        async with _async_client(test_app) as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                headers={"Authorization": "Bearer dummy"},
                json={
                    "current_password": "password123",
                    "new_password": "password123",
                },
            )

        assert resp.status_code == _HTTP_400
        assert "different from current" in resp.json()["detail"]

    async def test_short_new_password_returns_422(self, test_app):
        """Pydantic validator rejects new_password shorter than 8 chars."""
        user = _make_user_read()
        test_app.dependency_overrides[get_current_user] = lambda: user
        # get_auth_service must also be overridden — the real dependency
        # requires a live DB session, and body validation (422) happens
        # after dependency injection is attempted.
        test_app.dependency_overrides[get_auth_service] = lambda: AsyncMock(
            spec=AuthService
        )

        async with _async_client(test_app) as client:
            resp = await client.post(
                "/api/v1/auth/change-password",
                headers={"Authorization": "Bearer dummy"},
                json={
                    "current_password": "password123",
                    "new_password": "short",
                },
            )

        assert resp.status_code == _HTTP_422
