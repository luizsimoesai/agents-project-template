from aegra_api.models.assistants import Assistant as AegraAssistant
from aegra_api.models.assistants import AssistantCreate as AegraCreate
from aegra_api.models.assistants import AssistantUpdate as AegraUpdate

# Import Aegra's internal AssistantService and its FastAPI dependency factory.
# We wrap it rather than replacing it so that Aegra continues to handle:
#   - version management (assistant_versions table)
#   - system assistant visibility
#   - graph_id validation against aegra.json
#   - CASCADE delete of related runs
from aegra_api.services.assistant_service import AssistantService as AegraService
from aegra_api.services.assistant_service import (
    get_assistant_service as get_aegra_service,
)
from fastapi import Depends

from src.schemas.assistant import AssistantCreate, AssistantRead, AssistantUpdate


def _to_read(a: AegraAssistant) -> AssistantRead:
    """Convert an Aegra Assistant model to our public AssistantRead schema.

    The only non-trivial mapping is metadata: Aegra defines the field as
    `metadata = Field(alias="metadata_dict")`, meaning 'metadata_dict' is the
    JSON serialization key but the Python attribute is simply 'metadata'.
    """
    return AssistantRead(
        assistant_id=a.assistant_id,
        name=a.name,
        description=a.description,
        graph_id=a.graph_id,
        config=a.config,
        context=a.context,
        # Aegra defines: metadata = Field(alias="metadata_dict")
        # 'metadata_dict' is the JSON alias; the Python attribute is 'metadata'.
        metadata=a.metadata,
        version=a.version,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


class AssistantService:
    """Thin wrapper around Aegra's AssistantService.

    Responsibilities:
    - Translate our simplified schemas ↔ Aegra's schemas.
    - Pass user_identity (str(current_user.id)) so Aegra scopes queries to
      the authenticated user automatically.
    - Convert Aegra's response models to our AssistantRead.

    All user-ownership enforcement is handled inside Aegra's service:
    unauthorized access to another user's assistant returns a 404.
    """

    def __init__(self, _svc: AegraService) -> None:
        self._svc = _svc

    async def create(self, data: AssistantCreate, user_id: str) -> AssistantRead:
        """Create a new assistant owned by user_id."""
        aegra_data = AegraCreate(
            name=data.name,
            description=data.description,
            graph_id=data.graph_id,
            config=data.config,
            context=data.context,
            metadata=data.metadata,
        )
        result = await self._svc.create_assistant(aegra_data, user_identity=user_id)
        return _to_read(result)

    async def list(self, user_id: str) -> list[AssistantRead]:
        """Return all assistants owned by user_id (plus system assistants)."""
        results = await self._svc.list_assistants(user_identity=user_id)
        return [_to_read(a) for a in results]

    async def get(self, assistant_id: str, user_id: str) -> AssistantRead:
        """Fetch a single assistant by ID. 404 if not owned by user_id."""
        result = await self._svc.get_assistant(assistant_id, user_identity=user_id)
        return _to_read(result)

    async def update(
        self, assistant_id: str, data: AssistantUpdate, user_id: str
    ) -> AssistantRead:
        """Apply a partial update to an assistant. 404 if not owned by user_id."""
        aegra_data = AegraUpdate(
            name=data.name,
            description=data.description,
            config=data.config,
            context=data.context,
            metadata=data.metadata,
        )
        result = await self._svc.update_assistant(
            assistant_id, aegra_data, user_identity=user_id
        )
        return _to_read(result)

    async def delete(self, assistant_id: str, user_id: str) -> None:
        """Permanently delete an assistant. 404 if not owned by user_id.

        Aegra's CASCADE delete automatically removes related runs and versions.
        """
        await self._svc.delete_assistant(assistant_id, user_identity=user_id)


def get_assistant_service(
    _svc: AegraService = Depends(get_aegra_service),
) -> AssistantService:
    """FastAPI dependency factory for AssistantService.

    Follows the same Aegra pattern as get_user_service: FastAPI resolves
    Aegra's own get_aegra_service (which in turn resolves get_session and
    get_langgraph_service), and we wrap the result in our thin service layer.
    """
    return AssistantService(_svc)
