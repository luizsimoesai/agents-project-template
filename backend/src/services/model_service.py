import uuid

from aegra_api.core.orm import get_session
from fastapi import Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.llm_model import LLMModel
from src.schemas.llm_model import ModelCreate, ModelRead, ModelUpdate


class ModelService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _fetch_model(self, model_id: uuid.UUID) -> LLMModel:
        result = await self.session.execute(
            select(LLMModel).where(LLMModel.id == model_id)
        )
        m = result.scalar_one_or_none()
        if m is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model not found",
            )
        return m

    async def _set_default(self, model_id: uuid.UUID) -> ModelRead:
        """Clear is_default on all models, then set it on the given model.

        Both UPDATEs run inside a single ``session.begin()`` block so they
        commit together — if the second statement fails, the first is rolled
        back and the system never ends up with zero default models.
        """
        async with self.session.begin():
            await self.session.execute(update(LLMModel).values(is_default=False))
            await self.session.execute(
                update(LLMModel)
                .where(LLMModel.id == model_id)
                .values(is_default=True)
            )
        read = await self.get_model(model_id)
        # The UPDATE sets is_default=True in the DB; reflect this in the returned
        # schema even if the ORM object is still cached in the session.
        return read.model_copy(update={"is_default": True})

    async def create_model(self, data: ModelCreate) -> ModelRead:
        m = LLMModel(  # type: ignore[call-arg]
            display_name=data.display_name,
            model_id=data.model_id,
            provider=data.provider,
            description=data.description,
            base_url=data.base_url,
            is_active=data.is_active,
            is_default=False,
        )
        self.session.add(m)
        try:
            await self.session.commit()
            await self.session.refresh(m)
        except IntegrityError as err:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A model with this model_id already exists",
            ) from err
        if data.is_default:
            return await self._set_default(m.id)
        return ModelRead.model_validate(m)

    async def get_model(self, model_id: uuid.UUID) -> ModelRead:
        return ModelRead.model_validate(await self._fetch_model(model_id))

    async def list_active_models(self) -> list[ModelRead]:
        result = await self.session.execute(
            select(LLMModel).where(LLMModel.is_active.is_(True))
        )
        return [ModelRead.model_validate(m) for m in result.scalars().all()]

    async def list_all_models(self) -> list[ModelRead]:
        result = await self.session.execute(select(LLMModel))
        return [ModelRead.model_validate(m) for m in result.scalars().all()]

    async def update_model(self, model_id: uuid.UUID, data: ModelUpdate) -> ModelRead:
        m = await self._fetch_model(model_id)
        # exclude_unset → unsent fields keep their current value; nullable
        # fields can be cleared by passing an explicit ``null``.
        update_data = data.model_dump(exclude_unset=True, exclude={"is_default"})
        for field, value in update_data.items():
            setattr(m, field, value)
        await self.session.commit()
        await self.session.refresh(m)
        if data.is_default is True:
            return await self._set_default(model_id)
        return ModelRead.model_validate(m)

    async def delete_model(self, model_id: uuid.UUID) -> None:
        m = await self._fetch_model(model_id)
        if m.is_default:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Cannot delete the default model."
                    " Set another model as default first."
                ),
            )
        await self.session.delete(m)
        await self.session.commit()


def get_model_service(
    session: AsyncSession = Depends(get_session),
) -> ModelService:
    return ModelService(session)
