"""
Публичные API-схемы Telegram-профиля модуля users.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class TelegramRead(BaseModel):
    """Чтение Telegram-профиля текущего пользователя."""

    id: uuid.UUID
    telegram_id: str
    telegram_username: str | None = None
    telegram_first_name: str | None = None
    telegram_last_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
