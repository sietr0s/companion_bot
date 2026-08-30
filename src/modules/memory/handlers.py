"""Memory module bus event handlers."""

from src.bus.interface import MessageConsumer
from src.modules.memory.schemas_bus import (
    BuildContextCommand,
    ProcessBatchCommand,
    UpdateMemoryCommand,
)
from src.modules.memory.service import MemoryService


def register_handlers(consumer: MessageConsumer, service: MemoryService) -> None:
    """Register memory module event handlers."""

    consumer.subscribe(
        topic="memory.in",
        action="process_batch",
        schema=ProcessBatchCommand,
        handler=service.process_batch,
    )

    consumer.subscribe(
        topic="memory.in",
        action="build_context",
        schema=BuildContextCommand,
        handler=service.build_context,
    )

    consumer.subscribe(
        topic="memory.in",
        action="update_memory",
        schema=UpdateMemoryCommand,
        handler=service.update_memory,
    )
