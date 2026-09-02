"""Batching module bus handlers."""

from typing import Any

from src.bus.interface import MessageConsumer, MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.batching.schemas.events import AddMessageCommand
from src.modules.batching.service import BatchService


def register_handlers(consumer: MessageConsumer, producer: MessageProducer) -> None:
    service = BatchService(producer)

    @consumer.subscribe(BusTopics.BATCH_ADD_MESSAGE)
    async def handle_add_message(message: dict[str, Any]) -> None:
        command = AddMessageCommand.model_validate(message)
        await service.add_incoming_message(command)
