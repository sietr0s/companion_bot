"""Схемы категорий для CRUD API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    """Создание категории."""

    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=100, pattern=r"^[a-z0-9_]+$")
    description: str | None = None
    is_active: bool = True


class CategoryRead(BaseModel):
    """Просмотр категории."""

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CategoryUpdate(BaseModel):
    """Обновление категории (partial update)."""

    name: str | None = Field(default=None, max_length=100)
    description: str | None = None
    is_active: bool | None = None
