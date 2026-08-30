"""Схемы событий шины для модуля auth."""

import uuid

from pydantic import BaseModel


class UserRegistered(BaseModel):
    """Событие: пользователь зарегистрировался."""

    auth_id: uuid.UUID
    identifier: str
    identifier_type: str

    def to_bus_dict(self) -> dict:
        """Сериализация для шины событий."""
        return self.model_dump()


class UserLoggedIn(BaseModel):
    """Событие: пользователь вошёл."""

    auth_id: uuid.UUID
    identifier: str
    identifier_type: str

    def to_bus_dict(self) -> dict:
        """Сериализация для шины событий."""
        return self.model_dump()


class UserDeleted(BaseModel):
    """Событие: пользователь удалён."""

    auth_id: uuid.UUID

    def to_bus_dict(self) -> dict:
        """Сериализация для шины событий."""
        return self.model_dump()
