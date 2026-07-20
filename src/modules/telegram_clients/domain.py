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


class Sender(BaseModel):
    """Автор сообщения Telegram."""

    sender_id: int | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class Message(BaseModel):
    """Доменная модель сообщения Telegram."""

    account_id: uuid.UUID
    chat_id: int
    message_id: int
    sender: Sender
    text: str | None = None
    media: list[Media] = []
    date: datetime | None = None
