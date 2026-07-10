"""Public API-схемы настроек Telegram-аккаунта."""

from datetime import datetime

from pydantic import BaseModel


class TelegramSettingsRead(BaseModel):
    """Чтение настроек Telegram-аккаунта (public)."""

    read_groups: bool
    read_personal: bool
    read_channels: bool
    whitelist_chat_ids: list[str | int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TelegramSettingsUpdate(BaseModel):
    """Обновление настроек Telegram-аккаунта (public)."""

    read_groups: bool | None = None
    read_personal: bool | None = None
    read_channels: bool | None = None
    whitelist_chat_ids: list[str | int] | None = None
