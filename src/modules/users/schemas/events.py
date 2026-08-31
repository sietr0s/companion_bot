"""События шины модуля users."""

import uuid

from pydantic import BaseModel, Field

from src.core.bus_topics import BusTopics


class UserCreated(BaseModel):
    user_id: uuid.UUID
    telegram_id: int

    def to_bus_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["event_name"] = BusTopics.USER_CREATED
        return data


class UserUpdated(BaseModel):
    user_id: uuid.UUID
    telegram_id: int
    fields_updated: list[str] = Field(default_factory=list)

    def to_bus_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["event_name"] = BusTopics.USER_UPDATED
        return data
