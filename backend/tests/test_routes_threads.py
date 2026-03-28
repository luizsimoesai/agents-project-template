"""Integration tests for the /api/v1/threads routes.

All external dependencies (DB, LangGraph) are replaced with mocks so no
PostgreSQL connection is required. The test_app fixture (from conftest.py)
resets dependency_overrides before and after each test.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import HTTPException

from src.core.security import get_current_user
from src.schemas.thread import ChatResponse, MessageRead, ThreadRead
from src.schemas.user import UserRead
from src.services.assistant_service import AssistantService, get_assistant_service
from src.services.thread_service import ThreadService, get_thread_service

# ---------------------------------------------------------------------------
# HTTP status code constants (avoids PLR2004 magic-number warnings)
# ---------------------------------------------------------------------------

_HTTP_200 = 200
_HTTP_201 = 201
_HTTP_204 = 204
_HTTP_404 = 404

_EXPECTED_TWO_ITEMS = 2

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user_read() -> UserRead:
    return UserRead(
        id=uuid.uuid4(),
        name="Test User",
        email="test@example.com",
        is_admin=False,
        is_active=True,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _make_thread_read(thread_id=None, assistant_id="asst-1") -> ThreadRead:
    return ThreadRead(
        thread_id=thread_id or str(uuid.uuid4()),
        status="idle",
        assistant_id=assistant_id,
        thread_name="Test Thread",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _async_client(app) -> httpx.AsyncClient:
    """Return an AsyncClient wired to the given ASGI app."""
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# Shared fixture: mocked services + async HTTP client
# ---------------------------------------------------------------------------


@pytest.fixture
async def thread_client(test_app):
    """Yields (client, mock_thread_svc, mock_assistant_svc) with overrides applied."""
    test_user = _make_user_read()
    mock_thread_svc = AsyncMock(spec=ThreadService)
    mock_assistant_svc = AsyncMock(spec=AssistantService)

    test_app.dependency_overrides[get_current_user] = lambda: test_user
    test_app.dependency_overrides[get_thread_service] = lambda: mock_thread_svc
    test_app.dependency_overrides[get_assistant_service] = lambda: mock_assistant_svc

    async with _async_client(test_app) as client:
        yield client, mock_thread_svc, mock_assistant_svc


# ---------------------------------------------------------------------------
# POST /api/v1/threads
# ---------------------------------------------------------------------------


class TestCreateThread:
    async def test_create_thread_success(self, thread_client):
        client, mock_thread_svc, _ = thread_client
        thread = _make_thread_read(thread_id="t-1", assistant_id="asst-1")
        mock_thread_svc.create_thread.return_value = thread

        resp = await client.post(
            "/api/v1/threads",
            json={"assistant_id": "asst-1", "thread_name": "My Thread"},
        )

        assert resp.status_code == _HTTP_201
        body = resp.json()
        assert body["thread_id"] == "t-1"
        assert body["assistant_id"] == "asst-1"


# ---------------------------------------------------------------------------
# GET /api/v1/threads
# ---------------------------------------------------------------------------


class TestListThreads:
    async def test_list_threads_success(self, thread_client):
        client, mock_thread_svc, _ = thread_client
        threads = [
            _make_thread_read(thread_id="t-1"),
            _make_thread_read(thread_id="t-2"),
        ]
        mock_thread_svc.list_threads.return_value = threads

        resp = await client.get("/api/v1/threads")

        assert resp.status_code == _HTTP_200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == _EXPECTED_TWO_ITEMS


# ---------------------------------------------------------------------------
# GET /api/v1/threads/{thread_id}
# ---------------------------------------------------------------------------


class TestGetThread:
    async def test_get_thread_found(self, thread_client):
        client, mock_thread_svc, _ = thread_client
        thread = _make_thread_read(thread_id="t-42", assistant_id="asst-99")
        mock_thread_svc.get_thread.return_value = thread

        resp = await client.get("/api/v1/threads/t-42")

        assert resp.status_code == _HTTP_200
        body = resp.json()
        assert body["thread_id"] == "t-42"

    async def test_get_thread_not_found(self, thread_client):
        client, mock_thread_svc, _ = thread_client
        mock_thread_svc.get_thread.side_effect = HTTPException(
            status_code=_HTTP_404, detail="Thread not found"
        )

        resp = await client.get("/api/v1/threads/does-not-exist")

        assert resp.status_code == _HTTP_404


# ---------------------------------------------------------------------------
# DELETE /api/v1/threads/{thread_id}
# ---------------------------------------------------------------------------


class TestDeleteThread:
    async def test_delete_thread_success(self, thread_client):
        client, mock_thread_svc, _ = thread_client
        mock_thread_svc.delete_thread.return_value = None

        resp = await client.delete("/api/v1/threads/t-1")

        assert resp.status_code == _HTTP_204
        assert resp.content == b""


# ---------------------------------------------------------------------------
# POST /api/v1/threads/{thread_id}/chat
# ---------------------------------------------------------------------------


class TestChat:
    async def test_chat_success(self, thread_client):
        client, mock_thread_svc, mock_assistant_svc = thread_client
        thread = _make_thread_read(thread_id="t-1", assistant_id="asst-1")
        mock_thread_svc.get_thread.return_value = thread
        mock_assistant_svc.get.return_value = AsyncMock()
        mock_thread_svc.chat.return_value = ChatResponse(
            thread_id="t-1",
            message="Hello, how can I help you?",
            role="assistant",
        )

        resp = await client.post(
            "/api/v1/threads/t-1/chat",
            json={"message": "Hello"},
        )

        assert resp.status_code == _HTTP_200
        body = resp.json()
        assert "message" in body
        assert body["message"] == "Hello, how can I help you?"


# ---------------------------------------------------------------------------
# GET /api/v1/threads/{thread_id}/history
# ---------------------------------------------------------------------------


class TestGetHistory:
    async def test_get_history_with_messages(self, thread_client):
        client, mock_thread_svc, _ = thread_client
        history = [
            MessageRead(role="human", content="Hello"),
            MessageRead(role="ai", content="Hi there!"),
        ]
        mock_thread_svc.get_history.return_value = history

        resp = await client.get("/api/v1/threads/t-1/history")

        assert resp.status_code == _HTTP_200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == _EXPECTED_TWO_ITEMS
        assert body[0]["role"] == "human"
        assert body[0]["content"] == "Hello"
        assert body[1]["role"] == "ai"


# ---------------------------------------------------------------------------
# POST /api/v1/threads/{thread_id}/chat/stream
# ---------------------------------------------------------------------------


class TestStreamChat:
    async def test_stream_chat_success(self, thread_client):
        client, mock_thread_svc, mock_assistant_svc = thread_client
        thread = _make_thread_read(thread_id="t-1", assistant_id="asst-1")
        mock_thread_svc.get_thread.return_value = thread
        mock_assistant_svc.get.return_value = AsyncMock()

        async def fake_stream(*args, **kwargs):
            yield 'event: metadata\ndata: {"run_id": "r-1"}\n\n'
            yield 'event: end\ndata: {"status": "success"}\n\n'

        mock_thread_svc.stream_chat = fake_stream

        resp = await client.post(
            "/api/v1/threads/t-1/chat/stream",
            json={"message": "Hello"},
        )

        assert resp.status_code == _HTTP_200
        assert "text/event-stream" in resp.headers["content-type"]
        body = resp.text
        assert "event: metadata" in body
        assert "event: end" in body
