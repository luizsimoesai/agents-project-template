import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
from fastapi import HTTPException

from src.core.security import get_current_admin, get_current_user
from src.schemas.llm_model import ModelRead
from src.schemas.user import UserRead
from src.services.model_service import ModelService, get_model_service

_HTTP_200 = 200
_HTTP_201 = 201
_HTTP_204 = 204
_HTTP_401 = 401
_HTTP_403 = 403
_HTTP_404 = 404
_HTTP_409 = 409


def _make_user_read(**kwargs) -> UserRead:
    return UserRead(
        id=kwargs.get("id", uuid.uuid4()),
        name="Admin User",
        email="admin@example.com",
        is_admin=kwargs.get("is_admin", True),
        is_active=True,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _make_model_read(**kwargs) -> ModelRead:
    return ModelRead(
        id=kwargs.get("id", uuid.uuid4()),
        display_name=kwargs.get("display_name", "GPT-4o"),
        model_id=kwargs.get("model_id", "openai/gpt-4o"),
        provider=kwargs.get("provider", "openai"),
        description=None,
        base_url=None,
        is_active=kwargs.get("is_active", True),
        is_default=kwargs.get("is_default", False),
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _async_client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    )


def _raise_forbidden():
    raise HTTPException(status_code=_HTTP_403, detail="Admin access required")


# ── GET /api/v1/models ────────────────────────────────────────────────────────


async def test_list_active_models_requires_auth(test_app):
    async with _async_client(test_app) as client:
        res = await client.get("/api/v1/models")
    assert res.status_code == _HTTP_401


async def test_list_active_models_returns_active_only(test_app):
    models = [_make_model_read(is_active=True)]
    mock_service = AsyncMock(spec=ModelService)
    mock_service.list_active_models.return_value = models

    non_admin = _make_user_read(is_admin=False)
    test_app.dependency_overrides[get_current_user] = lambda: non_admin
    test_app.dependency_overrides[get_model_service] = lambda: mock_service

    async with _async_client(test_app) as client:
        res = await client.get("/api/v1/models")

    assert res.status_code == _HTTP_200
    data = res.json()
    assert len(data) == 1
    assert data[0]["model_id"] == "openai/gpt-4o"


# ── GET /api/v1/models/all ────────────────────────────────────────────────────


async def test_list_all_models_requires_admin(test_app):
    non_admin = _make_user_read(is_admin=False)
    test_app.dependency_overrides[get_current_user] = lambda: non_admin
    test_app.dependency_overrides[get_current_admin] = _raise_forbidden

    async with _async_client(test_app) as client:
        res = await client.get(
            "/api/v1/models/all",
            headers={"Authorization": "Bearer fake"},
        )

    assert res.status_code == _HTTP_403


async def test_list_all_models_returns_all(test_app):
    models = [
        _make_model_read(is_active=True),
        _make_model_read(model_id="openai/gpt-3.5-turbo", is_active=False),
    ]
    mock_service = AsyncMock(spec=ModelService)
    mock_service.list_all_models.return_value = models

    admin = _make_user_read()
    test_app.dependency_overrides[get_current_admin] = lambda: admin
    test_app.dependency_overrides[get_model_service] = lambda: mock_service

    async with _async_client(test_app) as client:
        res = await client.get("/api/v1/models/all")

    assert res.status_code == _HTTP_200
    assert len(res.json()) == len(models)


# ── POST /api/v1/models ───────────────────────────────────────────────────────


async def test_create_model_requires_admin(test_app):
    non_admin = _make_user_read(is_admin=False)
    test_app.dependency_overrides[get_current_user] = lambda: non_admin
    test_app.dependency_overrides[get_current_admin] = _raise_forbidden

    async with _async_client(test_app) as client:
        res = await client.post(
            "/api/v1/models",
            json={
                "display_name": "X",
                "model_id": "openai/gpt-4o",
                "provider": "openai",
            },
            headers={"Authorization": "Bearer fake"},
        )

    assert res.status_code == _HTTP_403


async def test_create_model_success(test_app):
    created = _make_model_read()
    mock_service = AsyncMock(spec=ModelService)
    mock_service.create_model.return_value = created

    admin = _make_user_read()
    test_app.dependency_overrides[get_current_admin] = lambda: admin
    test_app.dependency_overrides[get_model_service] = lambda: mock_service

    async with _async_client(test_app) as client:
        res = await client.post(
            "/api/v1/models",
            json={
                "display_name": "GPT-4o",
                "model_id": "openai/gpt-4o",
                "provider": "openai",
            },
        )

    assert res.status_code == _HTTP_201
    assert res.json()["model_id"] == "openai/gpt-4o"


# ── DELETE /api/v1/models/{id} ────────────────────────────────────────────────


async def test_delete_default_model_returns_409(test_app):
    mock_service = AsyncMock(spec=ModelService)
    mock_service.delete_model.side_effect = HTTPException(
        status_code=_HTTP_409,
        detail="Cannot delete the default model. Set another model as default first.",
    )

    admin = _make_user_read()
    test_app.dependency_overrides[get_current_admin] = lambda: admin
    test_app.dependency_overrides[get_model_service] = lambda: mock_service

    async with _async_client(test_app) as client:
        res = await client.delete(f"/api/v1/models/{uuid.uuid4()}")

    assert res.status_code == _HTTP_409


# ── PATCH /api/v1/models/{id} ─────────────────────────────────────────────────


async def test_update_model_requires_admin(test_app):
    test_app.dependency_overrides[get_current_admin] = lambda: (_ for _ in ()).throw(
        HTTPException(status_code=_HTTP_403, detail="Admin access required")
    )

    async with _async_client(test_app) as client:
        res = await client.patch(
            f"/api/v1/models/{uuid.uuid4()}",
            json={"display_name": "New Name"},
            headers={"Authorization": "Bearer fake"},
        )

    assert res.status_code == _HTTP_403


async def test_update_model_success(test_app):
    updated = _make_model_read(display_name="Updated Name")
    mock_service = AsyncMock(spec=ModelService)
    mock_service.update_model.return_value = updated

    admin = _make_user_read()
    test_app.dependency_overrides[get_current_admin] = lambda: admin
    test_app.dependency_overrides[get_model_service] = lambda: mock_service

    async with _async_client(test_app) as client:
        res = await client.patch(
            f"/api/v1/models/{uuid.uuid4()}",
            json={"display_name": "Updated Name"},
        )

    assert res.status_code == _HTTP_200
    assert res.json()["display_name"] == "Updated Name"
