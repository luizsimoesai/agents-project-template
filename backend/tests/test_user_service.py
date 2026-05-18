# backend/tests/test_user_service.py
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from src.schemas.user import UserCreate, UserUpdate
from src.services.user_service import UserService

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_refresh_side_effect(mock_session: AsyncMock) -> None:
    """Wire session.refresh to populate server-default timestamps on the ORM obj."""

    async def do_refresh(obj):
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now(UTC)
        if not getattr(obj, "updated_at", None):
            obj.updated_at = datetime.now(UTC)

    mock_session.refresh.side_effect = do_refresh


def _make_execute_result(rows: list) -> MagicMock:
    """Return a mock that mimics AsyncSession.execute() returning rows."""
    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = rows
    result.scalars.return_value = scalars_mock
    # scalar_one_or_none returns the first element or None
    result.scalar_one_or_none.return_value = rows[0] if rows else None
    return result


# ── create_user ───────────────────────────────────────────────────────────────


async def test_create_user_success(mock_session, user_factory):
    _make_refresh_side_effect(mock_session)
    service = UserService(mock_session)

    data = UserCreate(name="Alice", email="alice@example.com", password="securepass")
    result = await service.create_user(data)

    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()

    assert result.email == "alice@example.com"
    assert result.name == "Alice"

    # Verify the ORM object that was added has a bcrypt hash
    added_user = mock_session.add.call_args[0][0]
    assert added_user.password_hash.startswith("$2b$")


async def test_create_user_duplicate_email_raises_409(mock_session):
    _make_refresh_side_effect(mock_session)
    mock_session.commit.side_effect = IntegrityError(
        statement=None, params=None, orig=Exception("duplicate key")
    )
    service = UserService(mock_session)

    data = UserCreate(name="Bob", email="bob@example.com", password="securepass")
    with pytest.raises(HTTPException) as exc_info:
        await service.create_user(data)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    mock_session.rollback.assert_awaited_once()


def test_create_user_short_password_raises_validation_error():
    with pytest.raises(ValidationError):
        UserCreate(name="Carol", email="carol@example.com", password="short")


# ── get_user ──────────────────────────────────────────────────────────────────


async def test_get_user_found(mock_session, user_factory):
    user = user_factory(email="dave@example.com", name="Dave")
    mock_session.execute.return_value = _make_execute_result([user])
    service = UserService(mock_session)

    result = await service.get_user(user.id)

    assert result.email == "dave@example.com"
    assert result.name == "Dave"
    assert result.id == user.id


async def test_get_user_not_found_raises_404(mock_session):
    mock_session.execute.return_value = _make_execute_result([])
    service = UserService(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.get_user(uuid.uuid4())

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ── get_user_by_email ─────────────────────────────────────────────────────────


async def test_get_user_by_email_found(mock_session, user_factory):
    user = user_factory(email="eve@example.com")
    mock_session.execute.return_value = _make_execute_result([user])
    service = UserService(mock_session)

    result = await service.get_user_by_email("eve@example.com")

    assert result is user
    assert hasattr(result, "password_hash")


async def test_get_user_by_email_not_found(mock_session):
    mock_session.execute.return_value = _make_execute_result([])
    service = UserService(mock_session)

    result = await service.get_user_by_email("nobody@example.com")

    assert result is None


# ── list_users ────────────────────────────────────────────────────────────────


async def test_list_users_returns_user_read_list(mock_session, user_factory):
    users = [
        user_factory(email="f@example.com", name="Frank"),
        user_factory(email="g@example.com", name="Grace"),
    ]
    mock_session.execute.return_value = _make_execute_result(users)
    service = UserService(mock_session)

    result = await service.list_users()

    expected_count = 2
    assert len(result) == expected_count
    emails = {r.email for r in result}
    assert emails == {"f@example.com", "g@example.com"}


async def test_list_users_execute_called_once(mock_session, user_factory):
    mock_session.execute.return_value = _make_execute_result([])
    service = UserService(mock_session)

    await service.list_users(skip=5, limit=10)

    mock_session.execute.assert_awaited_once()


# ── update_user ───────────────────────────────────────────────────────────────


async def test_update_user_name_only(mock_session, user_factory):
    user = user_factory(name="Original", email="h@example.com")
    mock_session.execute.return_value = _make_execute_result([user])
    _make_refresh_side_effect(mock_session)
    service = UserService(mock_session)

    data = UserUpdate(name="Updated")
    result = await service.update_user(user.id, data)

    assert result.name == "Updated"
    assert result.email == "h@example.com"


async def test_update_user_email_only(mock_session, user_factory):
    user = user_factory(name="Ivan", email="old@example.com")
    mock_session.execute.return_value = _make_execute_result([user])
    _make_refresh_side_effect(mock_session)
    service = UserService(mock_session)

    data = UserUpdate(email="new@example.com")
    result = await service.update_user(user.id, data)

    assert result.email == "new@example.com"
    assert result.name == "Ivan"


async def test_update_user_not_found_raises_404(mock_session):
    mock_session.execute.return_value = _make_execute_result([])
    service = UserService(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.update_user(uuid.uuid4(), UserUpdate(name="X"))

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


async def test_update_user_duplicate_email_raises_409(mock_session, user_factory):
    user = user_factory(email="j@example.com")
    mock_session.execute.return_value = _make_execute_result([user])
    mock_session.commit.side_effect = IntegrityError(
        statement=None, params=None, orig=Exception("duplicate key")
    )
    service = UserService(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.update_user(user.id, UserUpdate(email="taken@example.com"))

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    mock_session.rollback.assert_awaited_once()


# ── set_user_active ───────────────────────────────────────────────────────────


async def test_set_user_active_true(mock_session, user_factory):
    user = user_factory(is_active=False)
    mock_session.execute.return_value = _make_execute_result([user])
    _make_refresh_side_effect(mock_session)
    service = UserService(mock_session)

    result = await service.set_user_active(user.id, True)

    assert result.is_active is True
    mock_session.commit.assert_awaited_once()


async def test_set_user_active_false(mock_session, user_factory):
    user = user_factory(is_active=True)
    mock_session.execute.return_value = _make_execute_result([user])
    _make_refresh_side_effect(mock_session)
    service = UserService(mock_session)

    result = await service.set_user_active(user.id, False)

    assert result.is_active is False


async def test_set_user_active_not_found_raises_404(mock_session):
    mock_session.execute.return_value = _make_execute_result([])
    service = UserService(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.set_user_active(uuid.uuid4(), True)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


# ── delete_user ───────────────────────────────────────────────────────────────


async def test_delete_user_success(mock_session, user_factory):
    user = user_factory(email="k@example.com")
    mock_session.execute.return_value = _make_execute_result([user])
    service = UserService(mock_session)

    await service.delete_user(user.id)

    mock_session.delete.assert_awaited_once_with(user)
    mock_session.commit.assert_awaited_once()


async def test_delete_user_not_found_raises_404(mock_session):
    mock_session.execute.return_value = _make_execute_result([])
    service = UserService(mock_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.delete_user(uuid.uuid4())

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
