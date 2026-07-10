"""
Internal API-схемы профиля пользователя модуля users.

auth_id передаётся в теле запроса (для межмодульного взаимодействия).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserRead(BaseModel):
    """Схема чтения профиля пользователя (internal)."""

    id: uuid.UUID
    auth_id: uuid.UUID
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    """Создание профиля пользователя (internal)."""

    auth_id: uuid.UUID
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None)


class UserUpdate(BaseModel):
    """Обновление профиля пользователя (internal)."""

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None)
