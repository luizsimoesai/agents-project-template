import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import bcrypt
import pytest
from aegra_api.services.langgraph_service import LangGraphService
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import create_access_token, create_refresh_token
from src.main import app
from src.models.llm_model import LLMModel
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
    """LangGraphService mock with get_graph() returning the context manager."""
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
        user = User(  # type: ignore[call-arg]
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
def model_factory():
    """Factory that creates LLMModel ORM instances for tests."""

    def make(**kwargs: Any) -> LLMModel:
        defaults: dict[str, Any] = {
            "display_name": "Test Model",
            "model_id": "openai/gpt-4o",
            "provider": "openai",
            "description": None,
            "base_url": None,
            "is_active": True,
            "is_default": False,
        }
        defaults.update(kwargs)
        m = LLMModel(  # type: ignore[call-arg]
            display_name=defaults["display_name"],
            model_id=defaults["model_id"],
            provider=defaults["provider"],
            description=defaults["description"],
            base_url=defaults["base_url"],
            is_active=defaults["is_active"],
            is_default=defaults["is_default"],
        )
        if not getattr(m, "id", None):
            m.id = uuid.uuid4()
        m.created_at = defaults.get("created_at", datetime.now(timezone.utc))
        m.updated_at = defaults.get("updated_at", datetime.now(timezone.utc))
        return m

    return make


@pytest.fixture
def test_app():
    """
    The FastAPI app with dependency_overrides reset before and after each test.
    Individual tests add their own overrides inside the test body.
    """
    app.dependency_overrides = {}
    yield app
    app.dependency_overrides = {}
