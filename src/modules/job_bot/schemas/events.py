"""
События модуля job_bot (шлюз Telegram).

Входящие сообщения от пользователя → публикуются в шину.
Исходящие сообщения → получаются из шины и отправляются через aiogram.
"""

from pydantic import BaseModel, Field

from src.bus.schemes import BaseEvent
from src.core.bus_topics import BusTopics


class TelegramUserInfo(BaseModel):
    """Данные автора входящего сообщения из Telegram."""

    telegram_id: int
    username: str | None = None
    first_name: str
    last_name: str | None = None


class BotMessageIncoming(BaseEvent):
    """
    Входящее сообщение от пользователя через Telegram-бота.

    Публикуется любым обработчиком aiogram (команда, текст, callback).
    job_matcher подписывается и обрабатывает бизнес-логику.
    """

    event_name: str = BusTopics.BOT_MESSAGE_INCOMING
    chat_id: int
    text: str
    command: str | None = None
    callback_data: str | None = None
    message_id: int | None = None
    user: TelegramUserInfo


class BotMessageOutgoing(BaseEvent):
    """
    Исходящее сообщение пользователю через Telegram-бота.

    Публикуется любым модулем (job_matcher, notifications).
    job_bot подписывается и отправляет через aiogram.
    """

    event_name: str = BusTopics.BOT_MESSAGE_OUTGOING
    chat_id: int
    text: str
    keyboard: dict | None = Field(default_factory=dict)


class BotMessageEdit(BaseEvent):
    """Команда Telegram-шлюзу отредактировать ранее отправленное сообщение."""

    event_name: str = BusTopics.BOT_MESSAGE_EDIT
    chat_id: int
    message_id: int
    text: str
    keyboard: dict | None = None
