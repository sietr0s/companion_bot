"""Memory module bus event handlers."""

import logging
from typing import Any

from src.bus.interface import MessageConsumer, MessageProducer
from src.core.bus_topics import BusTopics
from src.core.database import create_async_session
from src.modules.memory.dependencies import build_memory_service
from src.modules.memory.schemas.events import (
    BuildContextCommand,
    MaintainMemoryCommand,
    ProcessBatchCommand,
    UpdateMemoryCommand,
)

logger = logging.getLogger(__name__)


def register_handlers(consumer: MessageConsumer, producer: MessageProducer) -> None:
    service = build_memory_service(producer)

    @consumer.subscribe(BusTopics.MEMORY_PROCESS_BATCH)
    async def handle_process_batch(message: dict[str, Any]) -> None:
        command = ProcessBatchCommand.model_validate(message)
        async with create_async_session() as session:
            await service.process_batch(session, command)

    @consumer.subscribe(BusTopics.MEMORY_BUILD_CONTEXT)
    async def handle_build_context(message: dict[str, Any]) -> None:
        command = BuildContextCommand.model_validate(message)
        async with create_async_session() as session:
            await service.build_context(session, command)

    @consumer.subscribe(BusTopics.MEMORY_UPDATE)
    async def handle_update_memory(message: dict[str, Any]) -> None:
        command = UpdateMemoryCommand.model_validate(message)
        async with create_async_session() as session:
            await service.update_memory(session, command)

    @consumer.subscribe(BusTopics.MEMORY_MAINTAIN)
    async def handle_maintain(message: dict[str, Any]) -> None:
        command = MaintainMemoryCommand.model_validate(message)
        await _run_maintain(service, command)


async def _run_maintain(service, command: MaintainMemoryCommand) -> None:
    try:
        async with create_async_session() as session:
            await service.maintain_memory(session, command)
    except Exception:
        logger.exception("memory maintain failed conversation=%s", command.conversation_id)
