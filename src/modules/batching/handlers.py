"""Batching module bus handlers."""

from src.bus.interface import MessageConsumer
from src.modules.batching.schemas_bus import AddMessageCommand
from src.modules.batching.service import BatchService


async def handle_add_message(
    command: AddMessageCommand,
    service: BatchService,
) -> None:
    """Handle add message command."""
    await service.add_message(command)


def register_handlers(consumer: MessageConsumer, service: BatchService) -> None:
    """Register all batching module handlers."""
    consumer.subscribe(
        topic="batching.in",
        action="add_message",
        schema=AddMessageCommand,
        handler=lambda cmd: handle_add_message(cmd, service),
    )
