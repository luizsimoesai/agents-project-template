import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.security import get_current_admin, get_current_user
from src.schemas.user import UserCreate, UserRead, UserUpdate
from src.services.user_service import UserService, get_user_service

router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_current_user)],
)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    """Create a new user. Returns 409 if the email is already taken."""
    return await user_service.create_user(data)


@router.get(
    "",
    dependencies=[Depends(get_current_admin)],
)
async def list_users(
    user_service: Annotated[UserService, Depends(get_user_service)],
    skip: int = 0,
    limit: int = 100,
) -> list[UserRead]:
    """Return a paginated list of users. Admin only.

    Exposes name, email, and status of all accounts — restricted to admins
    to prevent authenticated users from enumerating the user base.

    skip: number of records to skip (OFFSET).
    limit: maximum number of records to return (LIMIT).
    """
    return await user_service.list_users(skip=skip, limit=limit)


@router.get(
    "/{user_id}",
    dependencies=[Depends(get_current_admin)],
)
async def get_user(
    user_id: uuid.UUID,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    """Fetch a single user by ID. Admin only.

    Returns 403 if the caller is not an admin, 404 if the user is not found.
    """
    return await user_service.get_user(user_id)


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_admin)],
)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    """Partially update a user (PATCH semantics: only sent fields are changed).

    Returns 404 if the user does not exist, 409 if the new email is taken.
    """
    return await user_service.update_user(user_id, data)


@router.patch(
    "/{user_id}/activate",
    dependencies=[Depends(get_current_admin)],
)
async def activate_user(
    user_id: uuid.UUID,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    """Set is_active=True for a user. Admin only.

    Returns 403 if the caller is not an admin, 404 if the user is not found.
    """
    return await user_service.set_user_active(user_id, is_active=True)


@router.patch(
    "/{user_id}/deactivate",
    dependencies=[Depends(get_current_admin)],
)
async def deactivate_user(
    user_id: uuid.UUID,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserRead:
    """Set is_active=False for a user. Admin only.

    A deactivated user can no longer log in or call any protected endpoint.
    Returns 403 if the caller is not an admin, 404 if the user is not found.
    """
    return await user_service.set_user_active(user_id, is_active=False)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)],
)
async def delete_user(
    user_id: uuid.UUID,
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> None:
    """Permanently delete a user by ID. Admin only.

    Returns 204 on success, 403 if the caller is not an admin, 404 if not found.
    """
    await user_service.delete_user(user_id)
