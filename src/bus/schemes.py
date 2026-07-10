"""
Базовый класс для событий шины сообщений.

Все события наследуются от BaseEvent, который обеспечивает
единый формат сериализации через model_dump() (Pydantic v2).
Метод to_bus_dict() добавляет поле event с именем топика.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """
    Базовый класс для всех событий шины сообщений.

    Автоматически проставляет timestamp в UTC.
    Каждый наследник определяет event_name как поле класса.
    """

    # Имя события (топик шины) — переопределяется в наследниках
    event_name: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_bus_dict(self) -> dict:
        """
        Сериализация события для шины сообщений.

        Использует встроенный model_dump() из Pydantic v2.
        UUID и datetime автоматически сериализуются в JSON-совместимые типы
        через mode="json".
        """
        return self.model_dump(mode="json")
