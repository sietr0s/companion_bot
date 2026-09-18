"""Bus handlers for Instagram send."""

import logging
import uuid
from typing import Any

from src.bus import get_consumer, get_producer
from src.bus.interface import MessageConsumer, MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.instagram_clients.adapters.client_manager import InstagramClientManager
from src.modules.instagram_clients.dependencies import get_instagram_client_manager
from src.modules.instagram_clients.schemas.events import IgMessageSent

logger = logging.getLogger(__name__)


def register_handlers(
    consumer: MessageConsumer | None = None,
    client_manager: InstagramClientManager | None = None,
    producer: MessageProducer | None = None,
) -> None:
    bus = consumer or get_consumer()

    @bus.subscribe(BusTopics.IG_MESSAGE_SEND)
    async def handle_send_message(message: dict[str, Any]) -> None:
        account_id = message.get("account_id")
        chat_id = message.get("chat_id")
        text = message.get("text", "")
        if not account_id or chat_id is None:
            logger.warning("Пропуск instagram send_message: нет account_id или chat_id")
            return
        manager = client_manager or get_instagram_client_manager()
        success = True
        error = None
        message_id = None
        try:
            message_id = await manager.send_text(uuid.UUID(str(account_id)), int(chat_id), text)
        except Exception as exc:
            success = False
            error = str(exc)
            logger.exception(
                "Не удалось отправить Instagram Direct: account=%s chat=%s",
                account_id,
                chat_id,
            )
        bus_producer = producer or get_producer()
        event = IgMessageSent(
            account_id=uuid.UUID(str(account_id)),
            chat_id=int(chat_id),
            text=text,
            message_id=message_id,
            success=success,
            error=error,
        )
        await bus_producer.publish(BusTopics.IG_MESSAGE_SENT, event.model_dump(mode="json"))
