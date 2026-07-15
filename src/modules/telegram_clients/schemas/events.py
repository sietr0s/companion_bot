"""
События модуля Telegram-клиентов.
"""

import uuid

from pydantic import BaseModel, Field

from src.bus.schemes import BaseEvent
from src.core.bus_topics import BusTopics


class Media(BaseModel):
    telegram_id: int
    type: str
    media_id: uuid.UUID | None = None


class TgMessageReceived(BaseEvent):
    """
    Событие: входящее сообщение из Telegram.

    Публикуется ClientManager при получении сообщения
    от любого подключённого аккаунта.

    media: list[dict] где каждый элемент содержит:
        - type: тип медиа (photo, video, voice, etc.)
        - id: Telegram file_id
        - file_id: ID файла в storage (после загрузки), может быть None
    """

    event_name: str = BusTopics.TG_MESSAGE_RECEIVED
    account_id: uuid.UUID
    chat_id: int
    message_id: int
    sender_id: int | None = None
    text: str | None = None
    media: list[Media] = Field(default_factory=list)


class TgMessageSend(BaseEvent):
    """
    Событие: отправить сообщение через Telegram-аккаунт.

    Модуль подписывается на этот топик и отправляет
    сообщение через указанный аккаунт.
    """

    event_name: str = BusTopics.TG_MESSAGE_SEND
    account_id: uuid.UUID
    chat_id: int
    text: str
    media: list[dict] = Field(default_factory=list)


class TgAccountConnected(BaseEvent):
    """Событие: Telegram-аккаунт подключён."""

    event_name: str = BusTopics.TG_ACCOUNT_CONNECTED
    account_id: uuid.UUID
    auth_id: uuid.UUID
    phone: str
    telegram_id: int | None = None


class TgAccountDisconnected(BaseEvent):
    """Событие: Telegram-аккаунт отключён."""

    event_name: str = BusTopics.TG_ACCOUNT_DISCONNECTED
    account_id: uuid.UUID
    auth_id: uuid.UUID
    reason: str  # "manual", "error", "deleted"
