"""Batching module bus handlers."""

from src.bus.interface import MessageConsumer
from src.core.database import create_async_session
from src.modules.batching.repository import BatchMessageRepository, BatchRepository
from src.modules.batching.schemas.events import AddMessageCommand
from src.modules.batching.service import BatchService


def register_handlers(consumer: MessageConsumer, producer) -> None:
    from src.core.bus_topics import BusTopics

    @consumer.subscribe(BusTopics.BATCH_ADD_MESSAGE)
    async def handle_add_message(message: dict) -> None:
        command = AddMessageCommand.model_validate(message)
        async with create_async_session() as session:
            service = BatchService(BatchRepository(), producer, BatchMessageRepository())
            await service.add_incoming_message(session, command)
