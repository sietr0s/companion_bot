"""
Internal API-схемы Telegram-профиля модуля users.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TelegramRead(BaseModel):
    """Чтение Telegram-профиля."""

    id: uuid.UUID
    telegram_id: str
    telegram_username: str | None = None
    telegram_first_name: str | None = None
    telegram_last_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TelegramCreate(BaseModel):
    """Создание Telegram-профиля (internal)."""

    telegram_id: str = Field(..., min_length=1, max_length=50)
    telegram_username: str | None = Field(default=None, max_length=100)
    telegram_first_name: str | None = Field(default=None, max_length=100)
    telegram_last_name: str | None = Field(default=None, max_length=100)


class TelegramUpdate(BaseModel):
    """Обновление Telegram-профиля (internal)."""

    telegram_username: str | None = Field(default=None, max_length=100)
    telegram_first_name: str | None = Field(default=None, max_length=100)
    telegram_last_name: str | None = Field(default=None, max_length=100)
