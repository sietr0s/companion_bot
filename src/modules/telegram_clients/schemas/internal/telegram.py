"""Internal API-схемы модуля Telegram-клиентов."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class TelegramAccountCreate(BaseModel):
    """Создание Telegram-аккаунта (internal)."""

    auth_id: uuid.UUID
    phone: str
    telegram_id: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    is_connected: bool = False


class TelegramAccountRead(BaseModel):
    """Чтение Telegram-аккаунта (internal)."""

    id: uuid.UUID
    auth_id: uuid.UUID
    phone: str
    is_connected: bool
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    telegram_id: int | None = None
    session_string: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TelegramAccountUpdate(BaseModel):
    """Обновление Telegram-аккаунта (internal)."""

    is_connected: bool | None = None
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    telegram_id: int | None = None
    session_string: str | None = None
