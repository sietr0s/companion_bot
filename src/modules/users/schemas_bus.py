"""Схемы событий шины для модуля users."""

import uuid

from pydantic import BaseModel


class ProfileCreated(BaseModel):
    """Событие: профиль пользователя создан."""

    auth_id: uuid.UUID
    profile_id: uuid.UUID

    def to_bus_dict(self) -> dict:
        """Сериализация для шины событий."""
        return self.model_dump()


class ProfileUpdated(BaseModel):
    """Событие: профиль пользователя обновлён."""

    auth_id: uuid.UUID
    profile_id: uuid.UUID
    fields_updated: list[str]

    def to_bus_dict(self) -> dict:
        """Сериализация для шины событий."""
        return self.model_dump()


class ProfileDeleted(BaseModel):
    """Событие: профиль пользователя удалён."""

    auth_id: uuid.UUID
    profile_id: uuid.UUID

    def to_bus_dict(self) -> dict:
        """Сериализация для шины событий."""
        return self.model_dump()
