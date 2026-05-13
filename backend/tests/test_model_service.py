import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, status

from src.schemas.llm_model import ModelCreate, ModelUpdate
from src.services.model_service import ModelService


def _make_refresh_side_effect(mock_session: AsyncMock) -> None:
    async def do_refresh(obj):
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now(timezone.utc)
        if not getattr(obj, "updated_at", None):
            obj.updated_at = datetime.now(timezone.utc)

    mock_session.refresh.side_effect = do_refresh


def _make_execute_result(rows: list) -> MagicMock:
    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = rows
    result.scalars.return_value = scalars_mock
    result.scalar_one_or_none.return_value = rows[0] if rows else None
    return result


# ── create_model ──────────────────────────────────────────────────────────────


async def test_create_model_success(mock_session, model_factory):
    _make_refresh_side_effect(mock_session)
    mock_session.execute.return_value = MagicMock()
    service = ModelService(mock_session)

    data = ModelCreate(
        display_name="GPT-4o",
        model_id="openai/gpt-4o",
        provider="openai",
    )
    result = await service.create_model(data)

    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited()
    assert result.display_name == "GPT-4o"
    assert result.model_id == "openai/gpt-4o"


async def test_create_model_with_is_default_calls_set_default(mock_session, model_factory):
    m = model_factory(model_id="openai/gpt-4o", is_active=True)
    _make_refresh_side_effect(mock_session)
    mock_session.execute.side_effect = [
        MagicMock(),  # UPDATE is_default=False
        MagicMock(),  # UPDATE is_default=True
        _make_execute_result([m]),  # SELECT for get_model
    ]
    service = ModelService(mock_session)

    data = ModelCreate(
        display_name="GPT-4o",
        model_id="openai/gpt-4o",
        provider="openai",
        is_default=True,
    )
    result = await service.create_model(data)

    assert result.is_default is True
    assert mock_session.execute.await_count >= 2


# ── get_model ─────────────────────────────────────────────────────────────────


async def test_get_model_found(mock_session, model_factory):
    m = model_factory(display_name="Claude", model_id="anthropic/claude-sonnet-4-6")
    mock_session.execute.return_value = _make_execute_result([m])
    service = ModelService(mock_session)

    result = await service.get_model(m.id)

    assert result.display_name == "Claude"
    assert result.model_id == "anthropic/claude-sonnet-4-6"


async def test_get_model_not_found_raises_404(mock_session):
    mock_session.execute.return_value = _make_execute_result([])
    service = ModelService(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_model(uuid.uuid4())

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ── list_models ───────────────────────────────────────────────────────────────


async def test_list_active_models_excludes_inactive(mock_session, model_factory):
    active = model_factory(model_id="openai/gpt-4o", is_active=True)
    mock_session.execute.return_value = _make_execute_result([active])
    service = ModelService(mock_session)

    result = await service.list_active_models()

    assert len(result) == 1
    assert result[0].model_id == "openai/gpt-4o"


async def test_list_all_models_returns_all(mock_session, model_factory):
    models = [
        model_factory(model_id="openai/gpt-4o", is_active=True),
        model_factory(model_id="openai/gpt-3.5-turbo", is_active=False),
    ]
    mock_session.execute.return_value = _make_execute_result(models)
    service = ModelService(mock_session)

    result = await service.list_all_models()

    assert len(result) == 2


# ── update_model ──────────────────────────────────────────────────────────────


async def test_update_model_display_name(mock_session, model_factory):
    m = model_factory(display_name="Old Name")
    mock_session.execute.return_value = _make_execute_result([m])
    _make_refresh_side_effect(mock_session)
    service = ModelService(mock_session)

    result = await service.update_model(m.id, ModelUpdate(display_name="New Name"))

    assert result.display_name == "New Name"
    mock_session.commit.assert_awaited()


async def test_update_model_not_found_raises_404(mock_session):
    mock_session.execute.return_value = _make_execute_result([])
    service = ModelService(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.update_model(uuid.uuid4(), ModelUpdate(display_name="X"))

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ── delete_model ──────────────────────────────────────────────────────────────


async def test_delete_model_success(mock_session, model_factory):
    m = model_factory(is_default=False)
    mock_session.execute.return_value = _make_execute_result([m])
    service = ModelService(mock_session)

    await service.delete_model(m.id)

    mock_session.delete.assert_awaited_once_with(m)
    mock_session.commit.assert_awaited_once()


async def test_delete_default_model_raises_409(mock_session, model_factory):
    m = model_factory(is_default=True)
    mock_session.execute.return_value = _make_execute_result([m])
    service = ModelService(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.delete_model(m.id)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
