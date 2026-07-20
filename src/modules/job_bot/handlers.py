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
from aiogram.types import CallbackQuery, Message, User

from src.bus import get_consumer, get_producer
from src.bus.interface import MessageConsumer, MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.job_bot.schemas.events import BotMessageIncoming, TelegramUserInfo
from src.modules.job_bot.service import BotService

logger = logging.getLogger(__name__)


def _telegram_user_info(user: User) -> TelegramUserInfo:
    """Преобразовать пользователя aiogram в контракт события шины."""
    return TelegramUserInfo(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )


def register_incoming_handlers(producer: MessageProducer | None = None) -> Router:
    """
    Регистрация aiogram-обработчиков для входящих сообщений.

    Все обработчики только публикуют события в шину.
    Бизнес-логика обрабатывается подписчиками (job_matcher).

    Returns:
        Router с зарегистрированными обработчиками.
    """
    producer = producer or get_producer()
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

        if message.from_user is None:
            logger.error(
                "Входящее сообщение не содержит автора Telegram: chat_id=%s",
                message.chat.id,
            )
            return

        # Извлекаем команду из первого слова
        command = None
        if message.text and message.text.startswith("/"):
            command = message.text.split()[0].split("@")[0]

        event = BotMessageIncoming(
            chat_id=message.chat.id,
            text=message.text or "",
            command=command,
            user=_telegram_user_info(message.from_user),
        )

        await producer.publish(
            BusTopics.BOT_MESSAGE_INCOMING,
            event.to_bus_dict(),
        )

    @router.callback_query()
    async def handle_callback_query(callback: CallbackQuery) -> None:
        """Опубликовать callback inline-кнопки в ту же шину команд бота."""
        if callback.message is None or callback.data is None:
            await callback.answer()
            return

        event = BotMessageIncoming(
            chat_id=callback.message.chat.id,
            text="",
            callback_data=callback.data,
            message_id=callback.message.message_id,
            user=_telegram_user_info(callback.from_user),
        )
        try:
            await producer.publish(
                BusTopics.BOT_MESSAGE_INCOMING,
                event.to_bus_dict(),
            )
        finally:
            await callback.answer()

    return router


def register_outgoing_handlers(
    consumer: MessageConsumer | None = None,
    bot_service: BotService | None = None,
) -> None:
    """
    Регистрация обработчиков шины для исходящих сообщений.

    Подписка на bot.message.outgoing — отправка сообщений пользователю через бота.
    """
    consumer = consumer or get_consumer()

    @consumer.subscribe(BusTopics.BOT_MESSAGE_OUTGOING)
    async def handle_outgoing_message(message: dict) -> None:
        """Обработчик: отправить сообщение пользователю через Telegram-бота."""
        chat_id = message.get("chat_id")
        text = message.get("text", "")
        keyboard = message.get("keyboard")

        if not chat_id or not text:
            logger.warning("Неполные данные для отправки: %s", message)
            return

        if bot_service is None:
            from src.modules.job_bot.dependencies import get_bot_service

            service = get_bot_service()
        else:
            service = bot_service

        await service.send_message(
            chat_id=int(chat_id),
            text=text,
            keyboard=keyboard,
        )

    @consumer.subscribe(BusTopics.BOT_MESSAGE_EDIT)
    async def handle_edit_message(message: dict) -> None:
        """Отредактировать текст и inline-клавиатуру сообщения бота."""
        chat_id = message.get("chat_id")
        message_id = message.get("message_id")
        text = message.get("text", "")
        keyboard = message.get("keyboard")

        if not chat_id or not message_id or not text:
            logger.warning("Неполные данные для редактирования сообщения: %s", message)
            return

        if bot_service is None:
            from src.modules.job_bot.dependencies import get_bot_service

            service = get_bot_service()
        else:
            service = bot_service

        await service.edit_message(
            chat_id=int(chat_id),
            message_id=int(message_id),
            text=text,
            keyboard=keyboard,
        )
