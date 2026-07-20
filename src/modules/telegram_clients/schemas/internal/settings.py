"""Internal API-схемы настроек Telegram-аккаунта."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class TelegramSettingsCreate(BaseModel):
    """Создание настроек Telegram-аккаунта (internal)."""

    use_whitelist: bool = True
    whitelist_chat_ids: list[str | int] = Field(default_factory=list)


class TelegramSettingsRead(BaseModel):
    """Чтение настроек Telegram-аккаунта (internal)."""

    id: uuid.UUID
    account_id: uuid.UUID
    use_whitelist: bool
    whitelist_chat_ids: list[str | int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TelegramSettingsUpdate(BaseModel):
    """Обновление настроек Telegram-аккаунта (internal)."""

    use_whitelist: bool | None = None
    whitelist_chat_ids: list[str | int] | None = None
