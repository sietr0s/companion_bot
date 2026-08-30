"""Bus schemas for telegram_clients module."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class Media(BaseModel):
    """Media attachment from Telegram."""

    telegram_id: int
    type: str


class Sender(BaseModel):
    """Message author from Telegram."""

    sender_id: int | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class TgMessageReceived(BaseModel):
    """Event: message received from Telegram."""

    telegram_account_id: uuid.UUID
    chat_id: int
    message_id: int
    sender: Sender
    text: str | None = None
    media: list[Media] = []
    date: datetime | None = None


class TgMessageSent(BaseModel):
    """Event: message sent to Telegram."""

    telegram_account_id: uuid.UUID
    chat_id: int
    message_id: int | None = None
    success: bool
    error: str | None = None


class TgAccountConnected(BaseModel):
    """Event: Telegram account connected."""

    account_id: uuid.UUID
    phone: str
    status: str


class TgAccountDisconnected(BaseModel):
    """Event: Telegram account disconnected."""

    account_id: uuid.UUID


class SendMessageCommand(BaseModel):
    """Command: send message to Telegram."""

    telegram_account_id: uuid.UUID
    chat_id: int
    text: str
    reply_to_message_id: int | None = None
    parse_mode: str | None = None


class DisconnectAccountCommand(BaseModel):
    """Command: disconnect Telegram account."""

    account_id: uuid.UUID
