"""Схемы для шины событий Example модуля."""

from pydantic import BaseModel, Field


class ExampleCreatedEvent(BaseModel):
    """Событие: Example создан."""

    event_name: str = "example.created"
    id: int
    name: str


class ExampleUpdatedEvent(BaseModel):
    """Событие: Example обновлен."""

    event_name: str = "example.updated"
    id: int
    name: str


class ExampleDeletedEvent(BaseModel):
    """Событие: Example удален."""

    event_name: str = "example.deleted"
    id: int
