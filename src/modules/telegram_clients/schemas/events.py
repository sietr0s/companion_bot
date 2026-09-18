"""Схемы событий шины модуля telegram_clients."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.bus.schemas import BaseEvent
from src.core.bus_topics import BusTopics
from src.domain.chat import Person, QuotedMessage

Sender = Person


class Media(BaseModel):
    telegram_id: int
    type: str


class TgMessageReceived(BaseEvent):
    event_name: str = BusTopics.TG_MESSAGE_RECEIVED
    channel: str = "telegram"
    account_id: UUID
    chat_id: int
    message_id: int
    sender: Person
    text: str | None = None
    media: list[Media] = Field(default_factory=list)
    date: datetime | None = None
    reply_to: QuotedMessage | None = None
    forward_from: QuotedMessage | None = None


class TgMessageSent(BaseEvent):
    event_name: str = BusTopics.TG_MESSAGE_SENT
    channel: str = "telegram"
    account_id: UUID
    chat_id: int
    text: str | None = None
    message_id: int | None = None
    success: bool
    error: str | None = None
    message_type: str = "text"


class TgAccountConnected(BaseEvent):
    event_name: str = BusTopics.TG_ACCOUNT_CONNECTED
    account_id: UUID
    phone: str
    status: str = "connected"
    telegram_id: int | None = None


class TgAccountDisconnected(BaseEvent):
    event_name: str = BusTopics.TG_ACCOUNT_DISCONNECTED
    account_id: UUID
    reason: str | None = None
