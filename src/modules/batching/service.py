"""Batching module service."""

from uuid import UUID

from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.batching.models import Batch, BatchMessage
from src.modules.batching.repository import BatchRepository
from src.modules.batching.schemas_bus import (
    AddMessageCommand,
    BatchCompletedEvent,
    BatchReadyEvent,
)


class BatchService:
    """Service for batch operations."""

    def __init__(
        self,
        repository: BatchRepository,
        message_bus: MessageProducer,
    ):
        self._repo = repository
        self._message_bus = message_bus

    async def create_batch(self, user_id: UUID, max_size: int = 10) -> Batch:
        """Create a new batch."""
        return await self._repo.create_batch(user_id=user_id, max_size=max_size)

    async def get_batch(self, batch_id: UUID) -> Batch:
        """Get a batch by ID."""
        return await self._repo.get_batch(batch_id)

    async def add_message(
        self, command: AddMessageCommand
    ) -> BatchMessage | BatchReadyEvent:
        """Add a message to a batch.

        Returns either the added message or BatchReadyEvent if batch is full.
        """
        message = await self._repo.add_message_to_batch(
            batch_id=command.batch_id,
            content=command.content,
            sequence_number=command.sequence_number,
        )

        # Get updated batch to check status
        batch = await self._repo.get_batch(command.batch_id)

        if batch.status == "ready":
            # Batch is full, publish ready event
            messages = await self._repo.get_batch_messages(batch.id)
            event = BatchReadyEvent(
                batch_id=batch.id,
                user_id=batch.user_id,
                message_count=len(messages),
                message_ids=[msg.id for msg in messages],
            )
            await self._message_bus.publish(
                topic=BusTopics.BATCH_READY,
                action="batch_ready",
                payload=event,
            )
            return event

        return message

    async def complete_batch(
        self, batch_id: UUID, success: bool = True, error_message: str | None = None
    ) -> None:
        """Mark a batch as completed and publish event."""
        batch = await self._repo.get_batch(batch_id)
        await self._repo.complete_batch(batch_id)

        event = BatchCompletedEvent(
            batch_id=batch_id,
            user_id=batch.user_id,
            success=success,
            error_message=error_message,
        )
        await self._message_bus.publish(
            topic=BusTopics.BATCH_COMPLETED,
            action="batch_completed",
            payload=event,
        )

    async def delete_batch(self, batch_id: UUID) -> None:
        """Delete a batch."""
        await self._repo.delete_batch(batch_id)

    async def get_batch_messages(self, batch_id: UUID) -> list[BatchMessage]:
        """Get all messages in a batch."""
        return await self._repo.get_batch_messages(batch_id)
