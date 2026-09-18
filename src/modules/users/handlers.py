"""Upsert собеседника по входящему сообщению канала."""

from typing import Any

from src.bus.interface import MessageConsumer, MessageProducer
from src.core.bus_topics import BusTopics
from src.core.database import create_async_session
from src.modules.users.dependencies import build_user_service


def register_handlers(
    consumer: MessageConsumer,
    producer: MessageProducer | None = None,
) -> None:
    @consumer.subscribe(BusTopics.TG_MESSAGE_RECEIVED)
    async def handle_telegram_message(message: dict[str, Any]) -> None:
        sender = message.get("sender") or {}
        sender_id = sender.get("sender_id")
        if sender_id is None:
            return
        service = build_user_service(producer)
        async with create_async_session() as session:
            await service.get_or_create_from_platform(
                session,
                platform="telegram",
                platform_user_id=str(sender_id),
                username=sender.get("username"),
                first_name=sender.get("first_name"),
                last_name=sender.get("last_name"),
            )
