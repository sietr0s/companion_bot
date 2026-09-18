"""События шины модуля users."""

from uuid import UUID

from pydantic import Field

from src.bus.schemas import BaseEvent
from src.core.bus_topics import BusTopics


class UserCreated(BaseEvent):
    event_name: str = BusTopics.USER_CREATED
    user_id: UUID
    platform: str
    platform_user_id: str


class UserUpdated(BaseEvent):
    event_name: str = BusTopics.USER_UPDATED
    user_id: UUID
    platform: str
    platform_user_id: str
    fields_updated: list[str] = Field(default_factory=list)
