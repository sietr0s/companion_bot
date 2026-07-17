"""
Обработчики событий модуля Telegram-клиентов.

Подписка на топик tg.message.send для отправки
сообщений через Telegram-аккаунты.
"""

import logging
import uuid

from src.bus import get_producer
from src.core.bus_topics import BusTopics
from src.modules.telegram_clients.dependencies import get_telegram_client_manager

logger = logging.getLogger(__name__)


def register_handlers() -> None:
    """
    Регистрация обработчиков событий на шину.

    client_manager передаётся явно, т.к. он не является
    частью DI-контейнера FastAPI.
    """
    bus = get_producer()

    @bus.subscribe(BusTopics.TG_MESSAGE_SEND)
    async def handle_send_message(message: dict) -> None:
        """Отправить сообщение через Telegram-аккаунт."""
        account_id = message.get("account_id")
        chat_id = message.get("chat_id")
        text = message.get("text", "")

        client_manager = get_telegram_client_manager()

        await client_manager.send_message(uuid.UUID(account_id), int(chat_id), text)
        logger.info(
            "Сообщение отправлено: account=%s, chat=%s",
            account_id,
            chat_id,
        )
