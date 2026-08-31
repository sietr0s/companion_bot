"""Upsert собеседника по входящему сообщению Telegram."""

from src.bus.interface import MessageConsumer, MessageProducer
from src.core.bus_topics import BusTopics
from src.core.database import create_async_session
from src.modules.users.repository import UserRepository
from src.modules.users.service import UserService


def register_handlers(
    consumer: MessageConsumer,
    producer: MessageProducer | None = None,
) -> None:
    @consumer.subscribe(BusTopics.TG_MESSAGE_RECEIVED)
    async def handle_telegram_message(message: dict) -> None:
        sender = message.get("sender") or {}
        telegram_id = sender.get("sender_id")
        if telegram_id is None:
            return
        from src.bus import get_producer

        service = UserService(
            repository=UserRepository(),
            message_bus=producer or get_producer(),
        )
        async with create_async_session() as session:
            await service.get_or_create_from_telegram(
                session,
                telegram_id=int(telegram_id),
                username=sender.get("username"),
                first_name=sender.get("first_name"),
                last_name=sender.get("last_name"),
            )
