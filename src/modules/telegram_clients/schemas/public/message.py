"""Схемы сообщения Telegram модуля telegram_clients."""

from datetime import datetime

from pydantic import BaseModel, Field

from .media import MediaItem


class MessageRead(BaseModel):
    """Схема чтения сообщения из Telegram API."""

    id: int
    chat_id: int
    sender_id: int | None = None
    text: str | None = None
    media: list[MediaItem] = Field(default_factory=list)
    date: datetime
