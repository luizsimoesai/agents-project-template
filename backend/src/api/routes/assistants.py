from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.security import get_current_user
from src.schemas.assistant import AssistantCreate, AssistantRead, AssistantUpdate
from src.schemas.user import UserRead
from src.services.assistant_service import AssistantService, get_assistant_service

# dependencies=[Depends(get_current_user)] applies JWT authentication to every
# route in this router — no need to repeat it on each handler.
# The authenticated user is also injected individually in each handler so we can
# pass str(current_user.id) as user_identity to the service layer.
router = APIRouter(
    prefix="/assistants",
    tags=["assistants"],
    dependencies=[Depends(get_current_user)],
)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_assistant(
    data: AssistantCreate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    assistant_service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> AssistantRead:
    """Create a new assistant owned by the authenticated user.

    graph_id defaults to "agent" (the only graph registered in aegra.json).
    Use context to configure the agent at runtime, for example:
      {"model": "anthropic/claude-sonnet-4-6", "system_prompt": "You are..."}
    """
    return await assistant_service.create(data, user_id=str(current_user.id))


@router.get("")
async def list_assistants(
    current_user: Annotated[UserRead, Depends(get_current_user)],
    assistant_service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> list[AssistantRead]:
    """Return all assistants owned by the authenticated user.

    System assistants (user_id="system") created by Aegra are also included.
    """
    return await assistant_service.list(user_id=str(current_user.id))


@router.get("/{assistant_id}")
async def get_assistant(
    assistant_id: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    assistant_service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> AssistantRead:
    """Fetch a single assistant by ID.

    Returns 404 if the assistant does not exist or belongs to another user.
    assistant_id is a string (UUID stored as TEXT in the Aegra table).
    """
    return await assistant_service.get(assistant_id, user_id=str(current_user.id))


@router.patch("/{assistant_id}")
async def update_assistant(
    assistant_id: str,
    data: AssistantUpdate,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    assistant_service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> AssistantRead:
    """Partially update an assistant (PATCH semantics: only sent fields change).

    Aegra automatically increments the version number on each update and stores
    the previous version in the assistant_versions table.
    Returns 404 if the assistant does not exist or belongs to another user.
    """
    return await assistant_service.update(
        assistant_id, data, user_id=str(current_user.id)
    )


@router.delete("/{assistant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assistant(
    assistant_id: str,
    current_user: Annotated[UserRead, Depends(get_current_user)],
    assistant_service: Annotated[AssistantService, Depends(get_assistant_service)],
) -> None:
    """Permanently delete an assistant and all its related runs and versions.

    Aegra handles CASCADE deletion of the assistant_versions and runs tables.
    Returns 204 on success, 404 if the assistant does not exist or belongs to
    another user.
    """
    await assistant_service.delete(assistant_id, user_id=str(current_user.id))
