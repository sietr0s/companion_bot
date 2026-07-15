"""
Доменные модели модуля telegram_clients.

Используются внутри модуля для представления
сообщений и медиа-вложений Telegram.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel


class Media(BaseModel):
    """Медиа-вложение из Telegram."""

    telegram_id: int
    type: str


class Message(BaseModel):
    """Доменная модель сообщения Telegram."""

    account_id: uuid.UUID
    chat_id: int
    message_id: int
    sender_id: int | None = None
    text: str | None = None
    media: list[Media] = []
    date: datetime | None = None
