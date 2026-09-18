"""
Обработчики событий модуля Telegram-клиентов.

Подписка на топик tg.message.send для отправки
сообщений через Telegram-аккаунты.
"""

import logging
import uuid
from pathlib import Path
from typing import Any

from src.bus import get_consumer, get_producer
from src.bus.interface import MessageConsumer, MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.telegram_clients.adapters.client_manager import TelegramClientManager
from src.modules.telegram_clients.dependencies import get_telegram_client_manager
from src.modules.telegram_clients.schemas.events import TgMessageSent

logger = logging.getLogger(__name__)


def register_handlers(
    consumer: MessageConsumer | None = None,
    client_manager: TelegramClientManager | None = None,
    producer: MessageProducer | None = None,
) -> None:
    """Регистрация обработчиков. client_manager — из контейнера, либо fallback DI."""
    bus = consumer or get_consumer()

    @bus.subscribe(BusTopics.TG_MESSAGE_SEND)
    async def handle_send_message(message: dict[str, Any]) -> None:
        """Отправить сообщение через Telegram-аккаунт."""
        account_id = message.get("account_id")
        chat_id = message.get("chat_id")
        text = message.get("text", "")
        if not account_id or chat_id is None:
            logger.warning("Пропуск send_message: нет account_id или chat_id")
            return

        manager = client_manager or get_telegram_client_manager()
        success = True
        error = None
        try:
            await manager.send_message(uuid.UUID(str(account_id)), int(chat_id), text)
        except Exception as exc:
            success = False
            error = str(exc)
            logger.exception(
                "Не удалось отправить сообщение: account=%s, chat=%s",
                account_id,
                chat_id,
            )
        else:
            logger.info(
                "Сообщение отправлено: account=%s, chat=%s",
                account_id,
                chat_id,
            )

        bus_producer = producer or get_producer()
        event = TgMessageSent(
            account_id=uuid.UUID(str(account_id)),
            chat_id=int(chat_id),
            text=text,
            success=success,
            error=error,
        )
        await bus_producer.publish(BusTopics.TG_MESSAGE_SENT, event.model_dump(mode="json"))

    @bus.subscribe(BusTopics.TG_CHAT_ACTION)
    async def handle_chat_action(message: dict[str, Any]) -> None:
        account_id = message.get("account_id")
        chat_id = message.get("chat_id")
        action = message.get("action") or "record_audio"
        if not account_id or chat_id is None:
            return
        manager = client_manager or get_telegram_client_manager()
        try:
            await manager.send_chat_action(uuid.UUID(str(account_id)), int(chat_id), action)
        except Exception:
            logger.exception("chat action failed account=%s chat=%s", account_id, chat_id)

    @bus.subscribe(BusTopics.TG_MESSAGE_SEND_VOICE)
    async def handle_send_voice(message: dict[str, Any]) -> None:
        account_id = message.get("account_id")
        chat_id = message.get("chat_id")
        path = message.get("path")
        text = message.get("text") or ""
        if not account_id or chat_id is None or not path:
            logger.warning("Пропуск send_voice: нет account_id, chat_id или path")
            return
        manager = client_manager or get_telegram_client_manager()
        success = True
        error = None
        try:
            await manager.send_voice(uuid.UUID(str(account_id)), int(chat_id), Path(path))
        except Exception as exc:
            success = False
            error = str(exc)
            logger.exception(
                "Не удалось отправить голосовое: account=%s chat=%s", account_id, chat_id
            )
        finally:
            Path(path).unlink(missing_ok=True)
        bus_producer = producer or get_producer()
        event = TgMessageSent(
            account_id=uuid.UUID(str(account_id)),
            chat_id=int(chat_id),
            text=text,
            success=success,
            error=error,
            message_type="voice",
        )
        await bus_producer.publish(BusTopics.TG_MESSAGE_SENT, event.model_dump(mode="json"))
