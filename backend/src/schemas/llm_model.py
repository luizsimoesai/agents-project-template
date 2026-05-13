import uuid
from datetime import datetime

from pydantic import BaseModel


class ModelCreate(BaseModel):
    display_name: str
    model_id: str
    provider: str
    description: str | None = None
    base_url: str | None = None
    is_active: bool = True
    is_default: bool = False


class ModelRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    display_name: str
    model_id: str
    provider: str
    description: str | None
    base_url: str | None
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime


class ModelUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    base_url: str | None = None
    is_active: bool | None = None
    is_default: bool | None = None
