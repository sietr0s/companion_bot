"""Схемы событий шины модуля auth."""

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel

from src.core.bus_topics import BusTopics


class UserRegistered(BaseModel):
    auth_id: uuid.UUID
    identifier: str
    identifier_type: str

    def to_bus_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["event_name"] = BusTopics.USER_REGISTERED
        data["timestamp"] = datetime.now(UTC).isoformat()
        return data


class UserLoggedIn(BaseModel):
    auth_id: uuid.UUID
    identifier: str
    identifier_type: str

    def to_bus_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["event_name"] = BusTopics.USER_LOGGED_IN
        data["timestamp"] = datetime.now(UTC).isoformat()
        return data


class UserDeleted(BaseModel):
    auth_id: uuid.UUID

    def to_bus_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["event_name"] = BusTopics.USER_DELETED
        data["timestamp"] = datetime.now(UTC).isoformat()
        return data
