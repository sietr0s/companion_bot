"""Схемы событий шины модуля instagram_clients."""

from uuid import UUID

from pydantic import Field

from src.bus.schemas import BaseEvent
from src.core.bus_topics import BusTopics
from src.domain.chat import Person


class IgMessageReceived(BaseEvent):
    event_name: str = BusTopics.IG_MESSAGE_RECEIVED
    channel: str = "instagram"
    account_id: UUID
    chat_id: int
    message_id: str
    sender: Person
    text: str | None = None
    media: list = Field(default_factory=list)


class IgMessageSent(BaseEvent):
    event_name: str = BusTopics.IG_MESSAGE_SENT
    channel: str = "instagram"
    account_id: UUID
    chat_id: int
    text: str | None = None
    message_id: str | None = None
    success: bool
    error: str | None = None


class IgAccountConnected(BaseEvent):
    event_name: str = BusTopics.IG_ACCOUNT_CONNECTED
    account_id: UUID
    username: str
    instagram_pk: int | None = None
    status: str = "connected"


class IgAccountDisconnected(BaseEvent):
    event_name: str = BusTopics.IG_ACCOUNT_DISCONNECTED
    account_id: UUID
    reason: str | None = None
