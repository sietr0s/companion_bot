"""
Публичные API-схемы профиля пользователя модуля users.

auth_id передаётся через JWT токен (header Authorization).
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    """
    Схема создания профиля.

    auth_id НЕ входит в схему — он пробрасывается из JWT-токена.
    Все остальные поля профиля опциональны.
    """

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None)


class UserRead(BaseModel):
    """Схема чтения профиля пользователя."""

    id: uuid.UUID
    auth_id: uuid.UUID
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """
    Схема обновления профиля.

    Все поля опциональны — поддерживается partial update.
    exclude_unset=True в сервисе гарантирует, что неуказанные
    поля не будут перезаписаны None-значениями.
    """

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None)
