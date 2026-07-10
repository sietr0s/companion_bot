"""Схемы media Telegram модуля telegram_clients."""

from pydantic import BaseModel


class MediaItem(BaseModel):
    """Элемент media в сообщении — заложено на будущее."""

    type: str  # "photo", "voice", "video", "document" и т.д.
    id: str  # Telegram file_id
    file_id: str | None = None  # ID файла в хранилище (после загрузки)
