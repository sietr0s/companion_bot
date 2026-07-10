"""
События модуля media.
"""

import uuid

from src.bus.schemes import BaseEvent
from src.core.bus_topics import BusTopics


class MediaUploaded(BaseEvent):
    """Событие: файл загружен."""

    event_name: str = BusTopics.MEDIA_UPLOADED
    file_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    is_public: bool


class MediaDeleted(BaseEvent):
    """Событие: файл удалён."""

    event_name: str = BusTopics.MEDIA_DELETED
    file_id: uuid.UUID
