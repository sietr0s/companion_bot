"""Public API-схемы настроек Telegram-аккаунта."""

from datetime import datetime

from pydantic import BaseModel


class TelegramSettingsRead(BaseModel):
    """Чтение настроек Telegram-аккаунта (public)."""

    use_whitelist: bool
    whitelist_chat_ids: list[str | int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TelegramSettingsUpdate(BaseModel):
    """Обновление настроек Telegram-аккаунта (public)."""

    use_whitelist: bool | None = None
    whitelist_chat_ids: list[str | int] | None = None
