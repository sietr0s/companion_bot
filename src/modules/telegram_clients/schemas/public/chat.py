"""Схемы чата Telegram модуля telegram_clients."""

from pydantic import BaseModel


class ChatRead(BaseModel):
    """Схема чтения чата из Telegram API."""

    id: int
    name: str | None = None
    chat_type: str  # "private", "group", "channel"
    username: str | None = None
    is_in_whitelist: bool = False
