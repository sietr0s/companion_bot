"""Internal API-схемы настроек Telegram-аккаунта."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TelegramSettingsCreate(BaseModel):
    """Создание настроек Telegram-аккаунта (internal)."""

    read_groups: bool = True
    read_personal: bool = True
    read_channels: bool = True
    whitelist_chat_ids: list[str | int] = Field(default_factory=list)


class TelegramSettingsRead(BaseModel):
    """Чтение настроек Telegram-аккаунта (internal)."""

    id: uuid.UUID
    account_id: uuid.UUID
    read_groups: bool
    read_personal: bool
    read_channels: bool
    whitelist_chat_ids: list[str | int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TelegramSettingsUpdate(BaseModel):
    """Обновление настроек Telegram-аккаунта (internal)."""

    read_groups: bool | None = None
    read_personal: bool | None = None
    read_channels: bool | None = None
    whitelist_chat_ids: list[str | int] | None = None
