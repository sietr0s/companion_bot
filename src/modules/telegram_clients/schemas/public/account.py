"""Схемы аккаунта Telegram модуля telegram_clients."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class AccountRead(BaseModel):
    """Схема чтения Telegram-аккаунта."""

    id: uuid.UUID
    phone: str
    is_connected: bool
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    telegram_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
