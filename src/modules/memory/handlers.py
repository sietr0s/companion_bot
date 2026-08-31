"""Memory module bus event handlers."""

from src.bus.interface import MessageConsumer, MessageProducer
from src.core.bus_topics import BusTopics
from src.core.database import create_async_session
from src.modules.llm.dependencies import get_llm_service
from src.modules.memory.repository import (
    ConversationRepository,
    MessageRepository,
    SummaryStateRepository,
    VectorRecordRepository,
)
from src.modules.memory.schemas.events import (
    BuildContextCommand,
    ProcessBatchCommand,
    UpdateMemoryCommand,
)
from src.modules.memory.service import MemoryService


def _service(producer: MessageProducer) -> MemoryService:
    return MemoryService(
        conversations=ConversationRepository(),
        messages=MessageRepository(),
        summaries=SummaryStateRepository(),
        vectors=VectorRecordRepository(),
        message_bus=producer,
        llm=get_llm_service(),
    )


def register_handlers(consumer: MessageConsumer, producer: MessageProducer) -> None:
    @consumer.subscribe(BusTopics.MEMORY_PROCESS_BATCH)
    async def handle_process_batch(message: dict) -> None:
        command = ProcessBatchCommand.model_validate(message)
        async with create_async_session() as session:
            await _service(producer).process_batch(session, command)

    @consumer.subscribe(BusTopics.MEMORY_BUILD_CONTEXT)
    async def handle_build_context(message: dict) -> None:
        command = BuildContextCommand.model_validate(message)
        async with create_async_session() as session:
            await _service(producer).build_context(session, command)

    @consumer.subscribe(BusTopics.MEMORY_UPDATE)
    async def handle_update_memory(message: dict) -> None:
        command = UpdateMemoryCommand.model_validate(message)
        async with create_async_session() as session:
            await _service(producer).update_memory(session, command)
