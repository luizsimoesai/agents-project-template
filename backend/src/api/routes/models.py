import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.core.security import get_current_admin, get_current_user
from src.schemas.llm_model import ModelCreate, ModelRead, ModelUpdate
from src.services.model_service import ModelService, get_model_service

router = APIRouter(
    prefix="/models",
    tags=["models"],
)


@router.get("", dependencies=[Depends(get_current_user)])
async def list_active_models(
    model_service: Annotated[ModelService, Depends(get_model_service)],
) -> list[ModelRead]:
    """List models visible to users (is_active=True)."""
    return await model_service.list_active_models()


@router.get("/all", dependencies=[Depends(get_current_admin)])
async def list_all_models(
    model_service: Annotated[ModelService, Depends(get_model_service)],
) -> list[ModelRead]:
    """List all models including inactive ones. Admin only."""
    return await model_service.list_all_models()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_admin)],
)
async def create_model(
    data: ModelCreate,
    model_service: Annotated[ModelService, Depends(get_model_service)],
) -> ModelRead:
    """Create a new model. Admin only."""
    return await model_service.create_model(data)


@router.patch("/{model_id}", dependencies=[Depends(get_current_admin)])
async def update_model(
    model_id: uuid.UUID,
    data: ModelUpdate,
    model_service: Annotated[ModelService, Depends(get_model_service)],
) -> ModelRead:
    """Partially update a model. Admin only."""
    return await model_service.update_model(model_id, data)


@router.delete(
    "/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)],
)
async def delete_model(
    model_id: uuid.UUID,
    model_service: Annotated[ModelService, Depends(get_model_service)],
) -> None:
    """Delete a model. Returns 409 if the model is the current default. Admin only."""
    await model_service.delete_model(model_id)
