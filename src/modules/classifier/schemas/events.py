"""События шины модуля classifier."""

import uuid

from pydantic import BaseModel, Field

from src.bus.schemes import BaseEvent
from src.core.bus_topics import BusTopics


class CategoryScore(BaseModel):
    """Результат классификации по категории."""

    id: uuid.UUID
    slug: str
    name: str
    confidence: float = Field(ge=0.0, le=1.0)


class TextClassifyRequest(BaseEvent):
    """
    Запрос на классификацию текста.

    Публикуется любым модулем для классификации текста.
    """

    event_name: str = BusTopics.TEXT_CLASSIFY_REQUEST
    request_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    text: str = Field(max_length=4000)


class TextClassifyCompleted(BaseEvent):
    """
    Результат классификации текста.

    Содержит все категории с confidence scores.
    """

    event_name: str = BusTopics.TEXT_CLASSIFY_COMPLETED
    request_id: uuid.UUID
    text_hash: str
    categories: list[CategoryScore]
    entities: dict = Field(default_factory=dict)
