"""Схемы событий шины модуля telegram_clients."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.core.bus_topics import BusTopics


class Media(BaseModel):
    telegram_id: int
    type: str


class Sender(BaseModel):
    sender_id: int | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class TgMessageReceived(BaseModel):
    account_id: uuid.UUID
    chat_id: int
    message_id: int
    sender: Sender
    text: str | None = None
    media: list[Media] = Field(default_factory=list)
    date: datetime | None = None

    def to_bus_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["event_name"] = BusTopics.TG_MESSAGE_RECEIVED
        return data


class TgMessageSent(BaseModel):
    telegram_account_id: uuid.UUID
    chat_id: int
    message_id: int | None = None
    success: bool
    error: str | None = None

    def to_bus_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["event_name"] = BusTopics.TG_MESSAGE_SENT
        return data


class TgAccountConnected(BaseModel):
    account_id: uuid.UUID
    phone: str
    status: str = "connected"
    telegram_id: int | None = None

    def to_bus_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["event_name"] = BusTopics.TG_ACCOUNT_CONNECTED
        return data


class TgAccountDisconnected(BaseModel):
    account_id: uuid.UUID
    reason: str | None = None

    def to_bus_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["event_name"] = BusTopics.TG_ACCOUNT_DISCONNECTED
        return data
