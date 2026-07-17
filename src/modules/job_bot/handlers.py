"""
Обработчики событий модуля job_bot (шлюз Telegram).

Входящие сообщения (aiogram handlers):
- Ловят сообщения от пользователей в Telegram
- Публикуют в топик bot.message.incoming
- Не содержат бизнес-логики — только транспорт

Исходящие сообщения (шина):
- Подписка на bot.message.outgoing
- Отправка сообщений через Telegram API
"""

import logging

from aiogram import Router
from aiogram.types import Message

from src.bus.interface import MessageBus
from src.core.bus_topics import BusTopics
from src.modules.job_bot.dependencies import get_bot_service
from src.modules.job_bot.schemas.events import BotMessageIncoming

logger = logging.getLogger(__name__)


def register_incoming_handlers(bus: MessageBus) -> Router:
    """
    Регистрация aiogram-обработчиков для входящих сообщений.

    Все обработчики только публикуют события в шину.
    Бизнес-логика обрабатывается подписчиками (job_matcher).

    Returns:
        Router с зарегистрированными обработчиками.
    """
    router = Router()

    @router.message()
    async def handle_incoming_message(message: Message) -> None:
        """
        Обработчик всех входящих сообщений.

        Публикует событие bot.message.incoming в шину.
        Извлекает команду из текста сообщения (если начинается с /).
        """
        logger.info(
            "Получено сообщение от chat_id=%s: %s",
            message.chat.id,
            message.text,
        )

        # Извлекаем команду из первого слова
        command = None
        if message.text and message.text.startswith("/"):
            command = message.text.split()[0].split("@")[0]

        event = BotMessageIncoming(
            chat_id=message.chat.id,
            text=message.text or "",
            command=command,
        )

        await bus.publish(
            BusTopics.BOT_MESSAGE_INCOMING,
            event.to_bus_dict(),
        )

    return router


def register_outgoing_handlers(bus: MessageBus) -> None:
    """
    Регистрация обработчиков шины для исходящих сообщений.

    Подписка на bot.message.outgoing — отправка сообщений пользователю через бота.

    Args:
        bus: Шина сообщений для подписки.
        bot_service: Сервис для отправки сообщений через Telegram API.
    """

    @bus.subscribe(BusTopics.BOT_MESSAGE_OUTGOING)
    async def handle_outgoing_message(message: dict) -> None:
        """Обработчик: отправить сообщение пользователю через Telegram-бота."""
        chat_id = message.get("chat_id")
        text = message.get("text", "")
        keyboard = message.get("keyboard")

        if not chat_id or not text:
            logger.warning("Неполные данные для отправки: %s", message)
            return

        service = get_bot_service()

        await service.send_message(
            chat_id=int(chat_id),
            text=text,
            keyboard=keyboard,
        )
