"""Схемы событий шины модуля auth."""

from uuid import UUID

from src.bus.schemas import BaseEvent
from src.core.bus_topics import BusTopics


class UserRegistered(BaseEvent):
    event_name: str = BusTopics.USER_REGISTERED
    auth_id: UUID
    identifier: str
    identifier_type: str


class UserLoggedIn(BaseEvent):
    event_name: str = BusTopics.USER_LOGGED_IN
    auth_id: UUID
    identifier: str
    identifier_type: str


class UserDeleted(BaseEvent):
    event_name: str = BusTopics.USER_DELETED
    auth_id: UUID
