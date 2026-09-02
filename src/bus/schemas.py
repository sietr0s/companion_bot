"""Базовый класс для событий шины сообщений."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    """Событие шины: timestamp UTC и event_name = топик."""

    event_name: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_bus_dict(self) -> dict:
        data = self.model_dump(mode="json")
        if self.event_name:
            data["event_name"] = self.event_name
        return data
