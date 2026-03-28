# Backend Test Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a comprehensive unit + integration test suite for the FastAPI/LangGraph backend, covering services, security, auth handler, and HTTP routes.

**Architecture:** Services are unit-tested with `AsyncMock(spec=AsyncSession)` + `AsyncMock(spec=LangGraphService)`. Routes are integration-tested with `httpx.AsyncClient` and `app.dependency_overrides` — no real DB, no real LangGraph.

**Tech Stack:** pytest ≥ 9, pytest-asyncio ≥ 0.24 (`asyncio_mode='auto'`), httpx ≥ 0.28, python-jose (already installed), bcrypt (already installed via passlib[bcrypt])

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/pyproject.toml` | Modify | Add `pytest-asyncio`, `httpx` to dev deps |
| `backend/tests/__init__.py` | Create | Empty, makes tests a package |
| `backend/tests/conftest.py` | Create | Shared fixtures: mock_session, mock_lg, mock_graph, user_factory, make_token, test_app |
| `backend/tests/test_security.py` | Create | Unit tests for create_access_token, create_refresh_token, decode_token, get_current_user, get_current_admin |
| `backend/tests/test_user_service.py` | Create | Unit tests for UserService (all methods) |
| `backend/tests/test_auth_service.py` | Create | Unit tests for AuthService.login and .refresh |
| `backend/tests/test_thread_service.py` | Create | Unit tests for ThreadService CRUD, chat, stream_chat, get_history |
| `backend/tests/test_auth_handler.py` | Create | Unit tests for `src.auth.jwt.authenticate` |
| `backend/tests/test_routes_auth.py` | Create | Integration tests for /api/v1/auth/* routes |
| `backend/tests/test_routes_threads.py` | Create | Integration tests for /api/v1/threads/* routes |

---

## Task 1: Add test dependencies and empty package file

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/tests/__init__.py`

- [ ] **Step 1: Add pytest-asyncio and httpx to dev dependencies**

In `backend/pyproject.toml`, update the `[dependency-groups]` section:

```toml
[dependency-groups]
dev = [
    "mypy>=1.19.1",
    "pytest>=9.0.2",
    "pytest-asyncio>=0.24",
    "pytest-cov>=7.1.0",
    "httpx>=0.28",
    "ruff>=0.15.7",
    "taskipy>=1.14.1",
]
```

- [ ] **Step 2: Install new dependencies**

Run from `backend/`:
```bash
uv sync
```
Expected: resolves without errors, `uv.lock` updated.

- [ ] **Step 3: Create empty package init**

Create `backend/tests/__init__.py` as an empty file.

- [ ] **Step 4: Verify pytest discovers tests directory**

```bash
cd backend && uv run pytest tests/ --collect-only 2>&1 | head -5
```
Expected: `no tests ran` (no test files yet) with exit code 0 or 5 (no tests found is OK).

- [ ] **Step 5: Commit**

```bash
cd backend && git add pyproject.toml uv.lock tests/__init__.py
git commit -m "chore: add pytest-asyncio and httpx to test dependencies"
```

---

## Task 2: Create conftest.py with shared fixtures

**Files:**
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Write conftest.py**

```python
# backend/tests/conftest.py
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import bcrypt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import create_access_token, create_refresh_token
from src.main import app
from src.models.user import User

# Pre-compute a bcrypt hash with low rounds (4) for test speed.
# Production uses rounds=12; we use 4 here so tests run in milliseconds.
_PLAIN_PASSWORD = "password123"
_PASSWORD_HASH = bcrypt.hashpw(
    _PLAIN_PASSWORD.encode(), bcrypt.gensalt(rounds=4)
).decode()


@pytest.fixture
def mock_session() -> AsyncMock:
    """AsyncSession mock with all commonly used methods pre-wired as AsyncMocks."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()  # add() is synchronous in SQLAlchemy
    return session


@pytest.fixture
def mock_graph() -> AsyncMock:
    """LangGraph graph mock that supports async context manager protocol."""
    graph = AsyncMock()
    graph.__aenter__ = AsyncMock(return_value=graph)
    graph.__aexit__ = AsyncMock(return_value=False)
    return graph


@pytest.fixture
def mock_lg(mock_graph: AsyncMock) -> AsyncMock:
    """LangGraphService mock whose get_graph() returns the mock_graph context manager."""
    from aegra_api.services.langgraph_service import LangGraphService

    lg = AsyncMock(spec=LangGraphService)
    lg.get_graph.return_value = mock_graph
    return lg


@pytest.fixture
def user_factory():
    """
    Factory that creates User ORM instances for tests.

    Usage:
        user = user_factory()                          # defaults
        user = user_factory(email="x@x.com", is_admin=True)
    """

    def make(**kwargs: Any) -> User:
        defaults: dict[str, Any] = {
            "email": "test@example.com",
            "password_hash": _PASSWORD_HASH,
            "name": "Test User",
            "is_admin": False,
            "is_active": True,
        }
        defaults.update(kwargs)
        user = User(
            email=defaults["email"],
            password_hash=defaults["password_hash"],
            name=defaults["name"],
            is_admin=defaults["is_admin"],
            is_active=defaults["is_active"],
        )
        # id is set by default_factory=uuid.uuid4 in the dataclass definition,
        # but created_at / updated_at only have server_default (DB-side), so we
        # must set them explicitly here to allow UserRead.model_validate(user).
        if not getattr(user, "id", None):
            user.id = uuid.uuid4()
        user.created_at = defaults.get("created_at", datetime.now(timezone.utc))
        user.updated_at = defaults.get("updated_at", datetime.now(timezone.utc))
        return user

    return make


@pytest.fixture
def make_token():
    """
    Factory that generates real signed JWTs for tests.

    Usage:
        token = make_token(user_id)                    # access token
        token = make_token(user_id, type="refresh")
    """

    def _make(user_id: uuid.UUID, type: str = "access") -> str:
        if type == "access":
            return create_access_token(user_id)
        return create_refresh_token(user_id)

    return _make


@pytest.fixture
def test_app():
    """
    The FastAPI app with dependency_overrides reset before and after each test.
    Individual tests add their own overrides inside the test body.
    """
    app.dependency_overrides = {}
    yield app
    app.dependency_overrides = {}
```

- [ ] **Step 2: Verify conftest imports without error**

```bash
cd backend && uv run pytest tests/ --collect-only 2>&1 | head -10
```
Expected: no import errors. Output may show `0 items` collected.

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add shared pytest fixtures (mock_session, user_factory, make_token)"
```

---

## Task 3: test_security.py — JWT creation and validation

**Files:**
- Create: `backend/tests/test_security.py`

- [ ] **Step 1: Write test_security.py**

```python
# backend/tests/test_security.py
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
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
    data = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert data["sub"] == str(user_id)
    assert data["type"] == "access"
    assert data["exp"] > datetime.now(timezone.utc).timestamp()


def test_create_refresh_token_claims():
    user_id = uuid.uuid4()
    token = create_refresh_token(user_id)
    data = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    assert data["sub"] == str(user_id)
    assert data["type"] == "refresh"
    # refresh token lifetime must be longer than access token lifetime
    access = create_access_token(user_id)
    access_data = jwt.decode(access, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
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
    # Passing an access token where a refresh token is expected
    with pytest.raises(HTTPException) as exc_info:
        decode_token(access_token, expected_type="refresh")
    assert exc_info.value.status_code == 401


def test_decode_token_invalid_signature_raises_401():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    tampered = token[:-4] + "XXXX"
    with pytest.raises(HTTPException) as exc_info:
        decode_token(tampered)
    assert exc_info.value.status_code == 401


def test_decode_token_expired_raises_401():
    user_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
    }
    expired_token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_token(expired_token)
    assert exc_info.value.status_code == 401


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
    assert exc_info.value.status_code == 401


async def test_get_current_user_inactive_raises_401(user_factory):
    user = user_factory(is_active=False)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.return_value = mock_result

    token = create_access_token(user.id)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=token, session=mock_session)
    assert exc_info.value.status_code == 401


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
    assert exc_info.value.status_code == 403
```

- [ ] **Step 2: Run and verify all pass**

```bash
cd backend && uv run pytest tests/test_security.py -v
```
Expected: all 10 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_security.py
git commit -m "test: add unit tests for JWT creation, decode_token, get_current_user, get_current_admin"
```

---

## Task 4: test_user_service.py — UserService unit tests

**Files:**
- Create: `backend/tests/test_user_service.py`

- [ ] **Step 1: Write test_user_service.py**

```python
# backend/tests/test_user_service.py
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from src.schemas.user import UserCreate, UserRead, UserUpdate
from src.services.user_service import UserService


def _make_service(mock_session):
    return UserService(mock_session)


def _mock_result(user=None, users=None):
    """Helper: build a mock result object for session.execute()."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    if users is not None:
        result.scalars.return_value.all.return_value = users
    return result


def _set_refresh_side_effect(mock_session):
    """Make session.refresh() populate server-generated fields on the object."""

    async def _refresh(obj):
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now(timezone.utc)
        if not getattr(obj, "updated_at", None):
            obj.updated_at = datetime.now(timezone.utc)

    mock_session.refresh.side_effect = _refresh


# ── create_user ──────────────────────────────────────────────────────────────

async def test_create_user_success(mock_session, user_factory):
    _set_refresh_side_effect(mock_session)
    service = _make_service(mock_session)
    data = UserCreate(name="Alice", email="alice@example.com", password="password123")

    result = await service.create_user(data)

    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
    assert isinstance(result, UserRead)
    assert result.email == "alice@example.com"
    assert not hasattr(result, "password_hash")
    # Verify that the stored hash is a valid bcrypt hash
    added_user = mock_session.add.call_args[0][0]
    assert added_user.password_hash.startswith("$2b$")


async def test_create_user_duplicate_email_raises_409(mock_session):
    mock_session.commit.side_effect = IntegrityError("unique", {}, None)
    service = _make_service(mock_session)
    data = UserCreate(name="Alice", email="alice@example.com", password="password123")

    with pytest.raises(HTTPException) as exc_info:
        await service.create_user(data)

    assert exc_info.value.status_code == 409
    mock_session.rollback.assert_awaited_once()


def test_create_user_short_password_raises_validation_error():
    with pytest.raises(ValidationError):
        UserCreate(name="Alice", email="alice@example.com", password="short")


# ── get_user ─────────────────────────────────────────────────────────────────

async def test_get_user_found(mock_session, user_factory):
    user = user_factory(email="bob@example.com")
    mock_session.execute.return_value = _mock_result(user=user)
    service = _make_service(mock_session)

    result = await service.get_user(user.id)

    assert isinstance(result, UserRead)
    assert result.email == "bob@example.com"


async def test_get_user_not_found_raises_404(mock_session):
    mock_session.execute.return_value = _mock_result(user=None)
    service = _make_service(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_user(uuid.uuid4())

    assert exc_info.value.status_code == 404


# ── get_user_by_email ─────────────────────────────────────────────────────────

async def test_get_user_by_email_found(mock_session, user_factory):
    user = user_factory(email="carol@example.com")
    mock_session.execute.return_value = _mock_result(user=user)
    service = _make_service(mock_session)

    result = await service.get_user_by_email("carol@example.com")

    # Returns raw User ORM object (with password_hash), not UserRead
    assert result is user
    assert hasattr(result, "password_hash")


async def test_get_user_by_email_not_found_returns_none(mock_session):
    mock_session.execute.return_value = _mock_result(user=None)
    service = _make_service(mock_session)

    result = await service.get_user_by_email("nobody@example.com")

    assert result is None


# ── list_users ────────────────────────────────────────────────────────────────

async def test_list_users_returns_all(mock_session, user_factory):
    users = [user_factory(email="a@example.com"), user_factory(email="b@example.com")]
    mock_session.execute.return_value = _mock_result(users=users)
    service = _make_service(mock_session)

    result = await service.list_users()

    assert len(result) == 2
    assert all(isinstance(u, UserRead) for u in result)


async def test_list_users_respects_skip_and_limit(mock_session, user_factory):
    mock_session.execute.return_value = _mock_result(users=[])
    service = _make_service(mock_session)

    await service.list_users(skip=10, limit=5)

    # The SQL query should have been called (we can't inspect internals easily,
    # but verifying execute was awaited is a minimal check)
    mock_session.execute.assert_awaited_once()


# ── update_user ───────────────────────────────────────────────────────────────

async def test_update_user_name_only(mock_session, user_factory):
    user = user_factory(email="dave@example.com", name="Dave")
    mock_session.execute.return_value = _mock_result(user=user)
    _set_refresh_side_effect(mock_session)
    service = _make_service(mock_session)

    result = await service.update_user(user.id, UserUpdate(name="David"))

    assert result.email == "dave@example.com"  # email unchanged
    assert user.name == "David"


async def test_update_user_email_only(mock_session, user_factory):
    user = user_factory(email="old@example.com", name="Eve")
    mock_session.execute.return_value = _mock_result(user=user)
    _set_refresh_side_effect(mock_session)
    service = _make_service(mock_session)

    await service.update_user(user.id, UserUpdate(email="new@example.com"))

    assert user.email == "new@example.com"
    assert user.name == "Eve"  # name unchanged


async def test_update_user_not_found_raises_404(mock_session):
    mock_session.execute.return_value = _mock_result(user=None)
    service = _make_service(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.update_user(uuid.uuid4(), UserUpdate(name="X"))

    assert exc_info.value.status_code == 404


async def test_update_user_duplicate_email_raises_409(mock_session, user_factory):
    user = user_factory()
    mock_session.execute.return_value = _mock_result(user=user)
    mock_session.commit.side_effect = IntegrityError("unique", {}, None)
    service = _make_service(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.update_user(user.id, UserUpdate(email="taken@example.com"))

    assert exc_info.value.status_code == 409
    mock_session.rollback.assert_awaited_once()


# ── set_user_active ───────────────────────────────────────────────────────────

async def test_set_user_active_true(mock_session, user_factory):
    user = user_factory(is_active=False)
    mock_session.execute.return_value = _mock_result(user=user)
    _set_refresh_side_effect(mock_session)
    service = _make_service(mock_session)

    await service.set_user_active(user.id, True)

    assert user.is_active is True
    mock_session.commit.assert_awaited_once()


async def test_set_user_active_false(mock_session, user_factory):
    user = user_factory(is_active=True)
    mock_session.execute.return_value = _mock_result(user=user)
    _set_refresh_side_effect(mock_session)
    service = _make_service(mock_session)

    await service.set_user_active(user.id, False)

    assert user.is_active is False


async def test_set_user_active_not_found_raises_404(mock_session):
    mock_session.execute.return_value = _mock_result(user=None)
    service = _make_service(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.set_user_active(uuid.uuid4(), True)

    assert exc_info.value.status_code == 404


# ── delete_user ───────────────────────────────────────────────────────────────

async def test_delete_user_success(mock_session, user_factory):
    user = user_factory()
    mock_session.execute.return_value = _mock_result(user=user)
    service = _make_service(mock_session)

    await service.delete_user(user.id)

    mock_session.delete.assert_awaited_once_with(user)
    mock_session.commit.assert_awaited_once()


async def test_delete_user_not_found_raises_404(mock_session):
    mock_session.execute.return_value = _mock_result(user=None)
    service = _make_service(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.delete_user(uuid.uuid4())

    assert exc_info.value.status_code == 404
```

- [ ] **Step 2: Run and verify all pass**

```bash
cd backend && uv run pytest tests/test_user_service.py -v
```
Expected: all 17 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_user_service.py
git commit -m "test: add unit tests for UserService (create, get, list, update, activate, delete)"
```

---

## Task 5: test_auth_service.py — AuthService unit tests

**Files:**
- Create: `backend/tests/test_auth_service.py`

- [ ] **Step 1: Write test_auth_service.py**

```python
# backend/tests/test_auth_service.py
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from jose import jwt

from src.core.settings import settings
from src.schemas.auth import LoginRequest, TokenResponse
from src.services.auth_service import AuthService


def _make_service(mock_session):
    return AuthService(mock_session)


def _mock_result(user=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    return result


# ── login ─────────────────────────────────────────────────────────────────────

async def test_login_success(mock_session, user_factory):
    user = user_factory(email="alice@example.com", is_active=True)
    mock_session.execute.return_value = _mock_result(user=user)
    service = _make_service(mock_session)

    result = await service.login(
        LoginRequest(email="alice@example.com", password="password123")
    )

    assert isinstance(result, TokenResponse)
    assert result.access_token
    assert result.refresh_token
    assert result.token_type == "bearer"


async def test_login_wrong_email_raises_401(mock_session):
    mock_session.execute.return_value = _mock_result(user=None)
    service = _make_service(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.login(
            LoginRequest(email="nobody@example.com", password="password123")
        )
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid credentials"


async def test_login_wrong_password_raises_401(mock_session, user_factory):
    user = user_factory(is_active=True)
    mock_session.execute.return_value = _mock_result(user=user)
    service = _make_service(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.login(
            LoginRequest(email=user.email, password="wrongpassword")
        )
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid credentials"


async def test_login_inactive_user_raises_401(mock_session, user_factory):
    user = user_factory(is_active=False)
    mock_session.execute.return_value = _mock_result(user=user)
    service = _make_service(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.login(
            LoginRequest(email=user.email, password="password123")
        )
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid credentials"


async def test_login_calls_verify_password_even_when_user_not_found(mock_session):
    """
    Security: _verify_password must be called even when user doesn't exist to
    prevent timing attacks that would reveal which emails are registered.
    """
    mock_session.execute.return_value = _mock_result(user=None)
    service = _make_service(mock_session)

    with patch("src.services.auth_service._verify_password") as mock_verify:
        mock_verify.return_value = False
        with pytest.raises(HTTPException):
            await service.login(
                LoginRequest(email="ghost@example.com", password="password123")
            )
        # Must be called — not short-circuited after discovering user is None
        mock_verify.assert_called_once()


# ── refresh ───────────────────────────────────────────────────────────────────

async def test_refresh_valid_token_returns_new_tokens(make_token):
    user_id = uuid.uuid4()
    refresh_token = make_token(user_id, type="refresh")
    # AuthService.refresh does not touch the DB, so no mock_session needed
    from sqlalchemy.ext.asyncio import AsyncSession
    service = _make_service(AsyncMock(spec=AsyncSession))

    result = await service.refresh(refresh_token)

    assert isinstance(result, TokenResponse)
    assert result.access_token
    assert result.refresh_token
    # New tokens must be different from the original (new expiry, new random jti if any)
    assert result.refresh_token != refresh_token


async def test_refresh_access_token_raises_401(make_token):
    user_id = uuid.uuid4()
    access_token = make_token(user_id, type="access")
    from sqlalchemy.ext.asyncio import AsyncSession
    service = _make_service(AsyncMock(spec=AsyncSession))

    with pytest.raises(HTTPException) as exc_info:
        await service.refresh(access_token)
    assert exc_info.value.status_code == 401


async def test_refresh_expired_token_raises_401():
    user_id = uuid.uuid4()
    expired_payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) - timedelta(days=1),
    }
    expired_token = jwt.encode(
        expired_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    from sqlalchemy.ext.asyncio import AsyncSession
    service = _make_service(AsyncMock(spec=AsyncSession))

    with pytest.raises(HTTPException) as exc_info:
        await service.refresh(expired_token)
    assert exc_info.value.status_code == 401
```

- [ ] **Step 2: Run and verify all pass**

```bash
cd backend && uv run pytest tests/test_auth_service.py -v
```
Expected: all 8 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_auth_service.py
git commit -m "test: add unit tests for AuthService login and refresh (including timing-safe check)"
```

---

## Task 6: test_thread_service.py — ThreadService unit tests

**Files:**
- Create: `backend/tests/test_thread_service.py`

- [ ] **Step 1: Write test_thread_service.py**

```python
# backend/tests/test_thread_service.py
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from src.schemas.thread import ChatResponse, MessageRead, ThreadCreate, ThreadRead
from src.services.thread_service import ThreadService


def _make_service(mock_session, mock_lg):
    return ThreadService(mock_session, mock_lg)


def _mock_thread(
    thread_id: str | None = None,
    user_id: str = "user-1",
    assistant_id: str = "asst-1",
    graph_id: str = "agent",
):
    """Create a mock AegraThread with all attributes needed by the service."""
    thread = MagicMock()
    thread.thread_id = thread_id or str(uuid.uuid4())
    thread.status = "idle"
    thread.metadata_json = {
        "assistant_id": assistant_id,
        "graph_id": graph_id,
        "owner": user_id,
        "thread_name": "Test Thread",
    }
    thread.user_id = user_id
    thread.created_at = datetime.now(timezone.utc)
    thread.updated_at = datetime.now(timezone.utc)
    return thread


def _mock_assistant(graph_id: str = "agent", context: dict | None = None):
    assistant = MagicMock()
    assistant.graph_id = graph_id
    assistant.context = context or {"model": "openai/gpt-4o-mini"}
    return assistant


def _mock_result(thread=None, threads=None):
    result = MagicMock()
    result.scalar_one_or_none.return_value = thread
    if threads is not None:
        result.scalars.return_value.all.return_value = threads
    return result


# ── create_thread ─────────────────────────────────────────────────────────────

async def test_create_thread_success(mock_session, mock_lg):
    async def do_refresh(obj):
        obj.created_at = datetime.now(timezone.utc)
        obj.updated_at = datetime.now(timezone.utc)

    mock_session.refresh.side_effect = do_refresh
    service = _make_service(mock_session, mock_lg)

    result = await service.create_thread(
        ThreadCreate(assistant_id="asst-1", thread_name="My Thread"),
        user_id="user-1",
    )

    assert isinstance(result, ThreadRead)
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()

    added = mock_session.add.call_args[0][0]
    meta = added.metadata_json
    assert meta["assistant_id"] == "asst-1"
    assert meta["graph_id"] == "agent"
    assert meta["owner"] == "user-1"
    assert meta["thread_name"] == "My Thread"


# ── list_threads ──────────────────────────────────────────────────────────────

async def test_list_threads_returns_user_threads(mock_session, mock_lg):
    threads = [_mock_thread(user_id="user-1"), _mock_thread(user_id="user-1")]
    mock_session.execute.return_value = _mock_result(threads=threads)
    service = _make_service(mock_session, mock_lg)

    result = await service.list_threads(user_id="user-1")

    assert len(result) == 2
    assert all(isinstance(t, ThreadRead) for t in result)


# ── get_thread ────────────────────────────────────────────────────────────────

async def test_get_thread_found(mock_session, mock_lg):
    thread = _mock_thread(thread_id="t-123", user_id="user-1")
    mock_session.execute.return_value = _mock_result(thread=thread)
    service = _make_service(mock_session, mock_lg)

    result = await service.get_thread("t-123", user_id="user-1")

    assert isinstance(result, ThreadRead)
    assert result.thread_id == "t-123"


async def test_get_thread_not_found_raises_404(mock_session, mock_lg):
    mock_session.execute.return_value = _mock_result(thread=None)
    service = _make_service(mock_session, mock_lg)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_thread("t-missing", user_id="user-1")

    assert exc_info.value.status_code == 404


# ── delete_thread ─────────────────────────────────────────────────────────────

async def test_delete_thread_success(mock_session, mock_lg):
    thread = _mock_thread(thread_id="t-del")
    mock_session.execute.return_value = _mock_result(thread=thread)
    service = _make_service(mock_session, mock_lg)

    await service.delete_thread("t-del", user_id="user-1")

    mock_session.delete.assert_awaited_once_with(thread)
    mock_session.commit.assert_awaited_once()


async def test_delete_thread_not_found_raises_404(mock_session, mock_lg):
    mock_session.execute.return_value = _mock_result(thread=None)
    service = _make_service(mock_session, mock_lg)

    with pytest.raises(HTTPException) as exc_info:
        await service.delete_thread("t-missing", user_id="user-1")

    assert exc_info.value.status_code == 404


# ── chat ──────────────────────────────────────────────────────────────────────

async def test_chat_success(mock_session, mock_lg, mock_graph):
    thread = _mock_thread(thread_id="t-1")
    mock_session.execute.return_value = _mock_result(thread=thread)
    mock_graph.ainvoke.return_value = {
        "messages": [HumanMessage(content="Hi"), AIMessage(content="Hello back!")]
    }
    assistant = _mock_assistant(graph_id="agent", context={"model": "openai/gpt-4o-mini"})
    service = _make_service(mock_session, mock_lg)

    result = await service.chat("t-1", "Hi", assistant)

    assert isinstance(result, ChatResponse)
    assert result.message == "Hello back!"
    assert result.thread_id == "t-1"


async def test_chat_passes_correct_config_and_context(mock_session, mock_lg, mock_graph):
    """graph.ainvoke must receive config with thread_id and context kwarg."""
    thread = _mock_thread(thread_id="t-cfg")
    mock_session.execute.return_value = _mock_result(thread=thread)
    mock_graph.ainvoke.return_value = {"messages": [AIMessage(content="ok")]}
    assistant = _mock_assistant(context={"model": "anthropic/claude-sonnet-4-6"})
    service = _make_service(mock_session, mock_lg)

    await service.chat("t-cfg", "test", assistant)

    _, call_kwargs = mock_graph.ainvoke.call_args
    assert call_kwargs.get("context") == {"model": "anthropic/claude-sonnet-4-6"}
    pos_args = mock_graph.ainvoke.call_args[0]
    config_arg = pos_args[1] if len(pos_args) > 1 else None
    assert config_arg == {"configurable": {"thread_id": "t-cfg"}}


async def test_chat_wrong_user_raises_404(mock_session, mock_lg):
    mock_session.execute.return_value = _mock_result(thread=None)
    service = _make_service(mock_session, mock_lg)

    with pytest.raises(HTTPException) as exc_info:
        await service.chat("t-other", "Hi", _mock_assistant())

    assert exc_info.value.status_code == 404
    # graph must NOT have been invoked
    mock_lg.get_graph.assert_not_called()


# ── get_history ───────────────────────────────────────────────────────────────

async def test_get_history_returns_messages(mock_session, mock_lg, mock_graph):
    thread = _mock_thread(thread_id="t-h", graph_id="agent")
    mock_session.execute.return_value = _mock_result(thread=thread)
    state = MagicMock()
    state.values = {
        "messages": [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
        ]
    }
    mock_graph.aget_state = AsyncMock(return_value=state)
    service = _make_service(mock_session, mock_lg)

    result = await service.get_history("t-h", user_id="user-1")

    assert len(result) == 2
    assert all(isinstance(m, MessageRead) for m in result)
    assert result[0].content == "Hello"
    assert result[1].content == "Hi there!"


async def test_get_history_empty_thread(mock_session, mock_lg, mock_graph):
    thread = _mock_thread(thread_id="t-empty")
    mock_session.execute.return_value = _mock_result(thread=thread)
    state = MagicMock()
    state.values = {"messages": []}
    mock_graph.aget_state = AsyncMock(return_value=state)
    service = _make_service(mock_session, mock_lg)

    result = await service.get_history("t-empty", user_id="user-1")

    assert result == []


async def test_get_history_uses_graph_id_from_metadata(mock_session, mock_lg, mock_graph):
    """get_graph must be called with the graph_id stored in metadata_json, not hardcoded."""
    thread = _mock_thread(thread_id="t-gid", graph_id="custom-agent")
    mock_session.execute.return_value = _mock_result(thread=thread)
    state = MagicMock()
    state.values = {}
    mock_graph.aget_state = AsyncMock(return_value=state)
    service = _make_service(mock_session, mock_lg)

    await service.get_history("t-gid", user_id="user-1")

    mock_lg.get_graph.assert_called_once()
    call_args = mock_lg.get_graph.call_args[0]
    assert call_args[0] == "custom-agent"


# ── stream_chat ───────────────────────────────────────────────────────────────

async def test_stream_chat_success(mock_session, mock_lg, mock_graph):
    thread = _mock_thread(thread_id="t-s")
    mock_session.execute.return_value = _mock_result(thread=thread)

    # Configure astream to yield one chunk then finish
    chunk = AIMessageChunk(content="Hello", id="msg-1")

    async def fake_astream(*args, **kwargs):
        yield ("messages", (chunk, {"langgraph_node": "call_model"}))

    mock_graph.astream = fake_astream
    assistant = _mock_assistant(context={"model": "openai/gpt-4o-mini"})
    service = _make_service(mock_session, mock_lg)

    events = []
    async for event in service.stream_chat("t-s", "Hi", assistant):
        events.append(event)

    # First event must be metadata, last must be end
    assert "event: metadata" in events[0]
    assert "event: end" in events[-1]
    assert '"status": "success"' in events[-1]
    # At least one messages/partial event for the chunk
    partial_events = [e for e in events if "event: messages/partial" in e]
    assert len(partial_events) >= 1


async def test_stream_chat_wrong_user_raises_404(mock_session, mock_lg):
    mock_session.execute.return_value = _mock_result(thread=None)
    service = _make_service(mock_session, mock_lg)

    with pytest.raises(HTTPException) as exc_info:
        # Must raise before first yield — consume the generator to trigger
        async for _ in service.stream_chat("t-x", "Hi", _mock_assistant()):
            pass

    assert exc_info.value.status_code == 404


async def test_stream_chat_graph_exception_yields_error_event(mock_session, mock_lg, mock_graph):
    thread = _mock_thread(thread_id="t-err")
    mock_session.execute.return_value = _mock_result(thread=thread)

    async def failing_astream(*args, **kwargs):
        raise RuntimeError("LangGraph exploded")
        yield  # make it an async generator

    mock_graph.astream = failing_astream
    service = _make_service(mock_session, mock_lg)

    events = []
    async for event in service.stream_chat("t-err", "Hi", _mock_assistant()):
        events.append(event)

    error_events = [e for e in events if "event: error" in e]
    assert len(error_events) == 1
    assert "RuntimeError" in error_events[0]


async def test_stream_chat_passes_context_kwarg(mock_session, mock_lg, mock_graph):
    """astream must receive context= from assistant.context."""
    thread = _mock_thread(thread_id="t-ctx")
    mock_session.execute.return_value = _mock_result(thread=thread)

    captured_kwargs: dict = {}

    async def capture_astream(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return
        yield  # async generator

    mock_graph.astream = capture_astream
    assistant = _mock_assistant(context={"system_prompt": "You are helpful"})
    service = _make_service(mock_session, mock_lg)

    async for _ in service.stream_chat("t-ctx", "Hi", assistant):
        pass

    assert captured_kwargs.get("context") == {"system_prompt": "You are helpful"}
```

- [ ] **Step 2: Run and verify all pass**

```bash
cd backend && uv run pytest tests/test_thread_service.py -v
```
Expected: all 17 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_thread_service.py
git commit -m "test: add unit tests for ThreadService (CRUD, chat, stream_chat, get_history)"
```

---

## Task 7: test_auth_handler.py — Aegra JWT handler

**Files:**
- Create: `backend/tests/test_auth_handler.py`

- [ ] **Step 1: Write test_auth_handler.py**

```python
# backend/tests/test_auth_handler.py
"""
Tests for src.auth.jwt.authenticate — the Aegra JWT handler.

We call authenticate() directly, bypassing Aegra's request pipeline,
since we don't spin up the full Aegra server in tests.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt
from langgraph_sdk import Auth

from src.auth.jwt import authenticate
from src.core.security import create_access_token, create_refresh_token
from src.core.settings import settings


async def test_valid_access_token_returns_identity():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)

    result = await authenticate({"authorization": f"Bearer {token}"})

    assert result["identity"] == str(user_id)
    assert "authenticated" in result["permissions"]


async def test_missing_authorization_header_raises_401():
    with pytest.raises(Auth.exceptions.HTTPException) as exc_info:
        await authenticate({})
    assert exc_info.value.status_code == 401


async def test_empty_token_after_bearer_raises_401():
    with pytest.raises(Auth.exceptions.HTTPException) as exc_info:
        await authenticate({"authorization": "Bearer "})
    assert exc_info.value.status_code == 401


async def test_invalid_signature_raises_401():
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    tampered = token[:-4] + "ZZZZ"

    with pytest.raises(Auth.exceptions.HTTPException) as exc_info:
        await authenticate({"authorization": f"Bearer {tampered}"})
    assert exc_info.value.status_code == 401


async def test_expired_token_raises_401():
    user_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
    }
    expired_token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    with pytest.raises(Auth.exceptions.HTTPException) as exc_info:
        await authenticate({"authorization": f"Bearer {expired_token}"})
    assert exc_info.value.status_code == 401


async def test_refresh_token_rejected():
    """Only access tokens are valid for API calls — refresh tokens must be rejected."""
    user_id = uuid.uuid4()
    refresh_token = create_refresh_token(user_id)

    with pytest.raises(Auth.exceptions.HTTPException) as exc_info:
        await authenticate({"authorization": f"Bearer {refresh_token}"})
    assert exc_info.value.status_code == 401


async def test_lowercase_authorization_header_key():
    """HTTP headers are case-insensitive; Aegra passes them lowercase."""
    user_id = uuid.uuid4()
    token = create_access_token(user_id)

    result = await authenticate({"authorization": f"Bearer {token}"})

    assert result["identity"] == str(user_id)
```

- [ ] **Step 2: Run and verify all pass**

```bash
cd backend && uv run pytest tests/test_auth_handler.py -v
```
Expected: all 7 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_auth_handler.py
git commit -m "test: add unit tests for Aegra JWT authenticate handler"
```

---

## Task 8: test_routes_auth.py — auth routes integration tests

**Files:**
- Create: `backend/tests/test_routes_auth.py`

- [ ] **Step 1: Write test_routes_auth.py**

```python
# backend/tests/test_routes_auth.py
"""
Integration tests for /api/v1/auth/* routes.

Strategy:
  - Override get_user_service and get_auth_service with AsyncMock instances
    so no real DB is needed.
  - For endpoints protected by get_current_user (/me), override it directly.
"""
import uuid
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

from src.core.security import create_access_token, get_current_user
from src.schemas.auth import TokenResponse
from src.schemas.user import UserCreate, UserRead
from src.services.auth_service import AuthService, get_auth_service
from src.services.user_service import UserService, get_user_service


@pytest.fixture
def mock_user_svc():
    return AsyncMock(spec=UserService)


@pytest.fixture
def mock_auth_svc():
    return AsyncMock(spec=AuthService)


@pytest.fixture
async def client(test_app, mock_user_svc, mock_auth_svc):
    test_app.dependency_overrides[get_user_service] = lambda: mock_user_svc
    test_app.dependency_overrides[get_auth_service] = lambda: mock_auth_svc
    async with httpx.AsyncClient(app=test_app, base_url="http://test") as ac:
        yield ac


def _make_user_read(**kwargs) -> UserRead:
    defaults = {
        "id": uuid.uuid4(),
        "name": "Test User",
        "email": "test@example.com",
        "is_admin": False,
        "is_active": True,
        "created_at": "2024-01-01T00:00:00+00:00",
    }
    defaults.update(kwargs)
    return UserRead(**defaults)


# ── POST /api/v1/auth/register ────────────────────────────────────────────────

async def test_register_success(client, mock_user_svc):
    user_read = _make_user_read(email="new@example.com")
    mock_user_svc.create_user.return_value = user_read

    resp = await client.post(
        "/api/v1/auth/register",
        json={"name": "New User", "email": "new@example.com", "password": "password123"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new@example.com"
    assert "password_hash" not in body


async def test_register_duplicate_email_returns_409(client, mock_user_svc):
    mock_user_svc.create_user.side_effect = HTTPException(
        status_code=409, detail="A user with this email already exists"
    )

    resp = await client.post(
        "/api/v1/auth/register",
        json={"name": "Alice", "email": "taken@example.com", "password": "password123"},
    )

    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


async def test_register_short_password_returns_422(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"name": "Alice", "email": "alice@example.com", "password": "short"},
    )

    assert resp.status_code == 422


# ── POST /api/v1/auth/login ───────────────────────────────────────────────────

async def test_login_success(client, mock_auth_svc):
    user_id = uuid.uuid4()
    token_response = TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token="refresh-token-value",
        token_type="bearer",
        expires_in=1800,
    )
    mock_auth_svc.login.return_value = token_response

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "password123"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


async def test_login_wrong_password_returns_401(client, mock_auth_svc):
    mock_auth_svc.login.side_effect = HTTPException(
        status_code=401, detail="Invalid credentials"
    )

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@example.com", "password": "wrongpass"},
    )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


async def test_login_inactive_user_returns_401(client, mock_auth_svc):
    mock_auth_svc.login.side_effect = HTTPException(
        status_code=401, detail="Invalid credentials"
    )

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "password123"},
    )

    assert resp.status_code == 401


# ── GET /api/v1/auth/me ───────────────────────────────────────────────────────

async def test_me_with_valid_token(test_app):
    """Override get_current_user directly so no DB is needed."""
    user_read = _make_user_read()
    test_app.dependency_overrides[get_current_user] = lambda: user_read

    async with httpx.AsyncClient(app=test_app, base_url="http://test") as ac:
        resp = await ac.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer fake-but-overridden"},
        )

    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


async def test_me_without_token_returns_401(test_app):
    """With no overrides, OAuth2PasswordBearer raises 401 when no Bearer token."""
    test_app.dependency_overrides = {}  # ensure clean state
    async with httpx.AsyncClient(app=test_app, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/auth/me")

    assert resp.status_code == 401


# ── POST /api/v1/auth/refresh ─────────────────────────────────────────────────

async def test_refresh_valid_token(client, mock_auth_svc):
    user_id = uuid.uuid4()
    new_tokens = TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token="new-refresh-token",
        token_type="bearer",
        expires_in=1800,
    )
    mock_auth_svc.refresh.return_value = new_tokens

    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "old-refresh-token"},
    )

    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_refresh_access_token_returns_401(client, mock_auth_svc):
    mock_auth_svc.refresh.side_effect = HTTPException(
        status_code=401, detail="Invalid token type"
    )

    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "this-is-actually-an-access-token"},
    )

    assert resp.status_code == 401
```

- [ ] **Step 2: Run and verify all pass**

```bash
cd backend && uv run pytest tests/test_routes_auth.py -v
```
Expected: all 11 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_routes_auth.py
git commit -m "test: add integration tests for auth routes (register, login, me, refresh)"
```

---

## Task 9: test_routes_threads.py — threads routes integration tests

**Files:**
- Create: `backend/tests/test_routes_threads.py`

- [ ] **Step 1: Write test_routes_threads.py**

```python
# backend/tests/test_routes_threads.py
"""
Integration tests for /api/v1/threads/* routes.

Strategy:
  - Override get_current_user to return a test UserRead (auth bypass).
  - Override get_thread_service and get_assistant_service with AsyncMocks.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import HTTPException

from src.core.security import get_current_user
from src.schemas.thread import ChatResponse, MessageRead, ThreadRead
from src.schemas.user import UserRead
from src.services.assistant_service import AssistantService, get_assistant_service
from src.services.thread_service import ThreadService, get_thread_service


_USER_ID = uuid.uuid4()
_USER_READ = UserRead(
    id=_USER_ID,
    name="Test User",
    email="test@example.com",
    is_admin=False,
    is_active=True,
    created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
)


def _make_thread_read(thread_id: str | None = None, assistant_id: str = "asst-1") -> ThreadRead:
    return ThreadRead(
        thread_id=thread_id or str(uuid.uuid4()),
        status="idle",
        assistant_id=assistant_id,
        thread_name="Test Thread",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_thread_svc():
    return AsyncMock(spec=ThreadService)


@pytest.fixture
def mock_assistant_svc():
    return AsyncMock(spec=AssistantService)


@pytest.fixture
async def client(test_app, mock_thread_svc, mock_assistant_svc):
    test_app.dependency_overrides[get_current_user] = lambda: _USER_READ
    test_app.dependency_overrides[get_thread_service] = lambda: mock_thread_svc
    test_app.dependency_overrides[get_assistant_service] = lambda: mock_assistant_svc
    async with httpx.AsyncClient(app=test_app, base_url="http://test") as ac:
        yield ac


# ── POST /api/v1/threads ──────────────────────────────────────────────────────

async def test_create_thread_returns_201(client, mock_thread_svc):
    thread_read = _make_thread_read(assistant_id="asst-42")
    mock_thread_svc.create_thread.return_value = thread_read

    resp = await client.post(
        "/api/v1/threads",
        json={"assistant_id": "asst-42", "thread_name": "My Chat"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["assistant_id"] == "asst-42"
    assert "thread_id" in body


# ── GET /api/v1/threads ───────────────────────────────────────────────────────

async def test_list_threads_returns_200(client, mock_thread_svc):
    threads = [_make_thread_read(), _make_thread_read()]
    mock_thread_svc.list_threads.return_value = threads

    resp = await client.get("/api/v1/threads")

    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── GET /api/v1/threads/{id} ──────────────────────────────────────────────────

async def test_get_thread_returns_200(client, mock_thread_svc):
    thread_id = str(uuid.uuid4())
    mock_thread_svc.get_thread.return_value = _make_thread_read(thread_id=thread_id)

    resp = await client.get(f"/api/v1/threads/{thread_id}")

    assert resp.status_code == 200
    assert resp.json()["thread_id"] == thread_id


async def test_get_thread_not_found_returns_404(client, mock_thread_svc):
    mock_thread_svc.get_thread.side_effect = HTTPException(status_code=404)

    resp = await client.get(f"/api/v1/threads/{uuid.uuid4()}")

    assert resp.status_code == 404


# ── DELETE /api/v1/threads/{id} ───────────────────────────────────────────────

async def test_delete_thread_returns_204(client, mock_thread_svc):
    mock_thread_svc.delete_thread.return_value = None

    resp = await client.delete(f"/api/v1/threads/{uuid.uuid4()}")

    assert resp.status_code == 204
    assert resp.content == b""


# ── POST /api/v1/threads/{id}/chat ────────────────────────────────────────────

async def test_chat_returns_agent_reply(client, mock_thread_svc, mock_assistant_svc):
    thread_id = str(uuid.uuid4())
    mock_thread_svc.get_thread.return_value = _make_thread_read(thread_id=thread_id)
    mock_assistant_svc.get.return_value = MagicMock()
    mock_thread_svc.chat.return_value = ChatResponse(
        thread_id=thread_id, message="The answer is 42"
    )

    resp = await client.post(
        f"/api/v1/threads/{thread_id}/chat",
        json={"message": "What is the answer?"},
    )

    assert resp.status_code == 200
    assert resp.json()["message"] == "The answer is 42"


# ── GET /api/v1/threads/{id}/history ─────────────────────────────────────────

async def test_get_history_returns_messages(client, mock_thread_svc):
    thread_id = str(uuid.uuid4())
    messages = [
        MessageRead(role="human", content="Hello"),
        MessageRead(role="ai", content="Hi!"),
    ]
    mock_thread_svc.get_history.return_value = messages

    resp = await client.get(f"/api/v1/threads/{thread_id}/history")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["role"] == "human"
    assert body[1]["role"] == "ai"


# ── POST /api/v1/threads/{id}/chat/stream ────────────────────────────────────

async def test_stream_chat_returns_sse_events(client, mock_thread_svc, mock_assistant_svc):
    """Verify Content-Type and that metadata + end events appear in the response body."""
    thread_id = str(uuid.uuid4())
    mock_thread_svc.get_thread.return_value = _make_thread_read(thread_id=thread_id)
    mock_assistant_svc.get.return_value = MagicMock()

    async def fake_stream(*args, **kwargs):
        yield 'event: metadata\ndata: {"run_id": "r-1", "attempt": 1}\n\n'
        yield 'event: end\ndata: {"status": "success"}\n\n'

    mock_thread_svc.stream_chat = fake_stream

    resp = await client.post(
        f"/api/v1/threads/{thread_id}/chat/stream",
        json={"message": "Hi"},
    )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    assert "event: metadata" in resp.text
    assert "event: end" in resp.text
```

- [ ] **Step 2: Run and verify all pass**

```bash
cd backend && uv run pytest tests/test_routes_threads.py -v
```
Expected: all 8 tests PASS.

- [ ] **Step 3: Run full suite and verify coverage**

```bash
cd backend && uv run pytest tests/ -v --cov=src --cov-report=term-missing 2>&1 | tail -30
```
Expected: all tests pass, coverage ≥ targets in spec.

- [ ] **Step 4: Commit**

```bash
git add tests/test_routes_threads.py
git commit -m "test: add integration tests for thread routes (CRUD, chat, stream, history)"
```

---

## Self-Review

### Spec Coverage

| Spec Section | Covered By |
|---|---|
| `UserService` all methods | Task 4 |
| `AuthService.login` + timing-safe | Task 5 |
| `AuthService.refresh` | Task 5 |
| `create/decode/create_refresh_token` | Task 3 |
| `get_current_user` / `get_current_admin` | Task 3 |
| `ThreadService` CRUD | Task 6 |
| `ThreadService.chat` + context | Task 6 |
| `ThreadService.stream_chat` all cases | Task 6 |
| `ThreadService.get_history` + graph_id | Task 6 |
| `src.auth.jwt.authenticate` all cases | Task 7 |
| Auth routes (register/login/me/refresh) | Task 8 |
| Thread routes + streaming | Task 9 |
| Add pytest-asyncio, httpx deps | Task 1 |

### No Placeholders — Confirmed

All steps have complete code. No "TBD" or "similar to above".

### Type Consistency

- `user_factory` returns `User` ORM objects throughout.
- `_make_thread_read` returns `ThreadRead` (schema) throughout.
- `mock_graph.ainvoke` is an `AsyncMock`; `mock_graph.astream` is replaced per-test with an `async def` generator.
- `_set_refresh_side_effect` pattern used consistently in Task 4.
