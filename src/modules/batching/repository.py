"""Batching module repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.batching.exceptions import BatchNotFoundError
from src.modules.batching.models import Batch, BatchMessage


class BatchRepository:
    """Repository for batch operations."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_batch(self, batch_id: UUID) -> Batch:
        """Get a batch by ID."""
        result = await self._session.execute(
            select(Batch).where(Batch.id == batch_id)
        )
        batch = result.scalar_one_or_none()
        if not batch:
            raise BatchNotFoundError(f"Batch {batch_id} not found")
        return batch

    async def create_batch(
        self, user_id: UUID, max_size: int = 10
    ) -> Batch:
        """Create a new batch."""
        from uuid import uuid4

        batch = Batch(
            id=uuid4(),
            user_id=user_id,
            max_size=max_size,
            current_size=0,
        )
        self._session.add(batch)
        await self._session.flush()
        return batch

    async def add_message_to_batch(
        self, batch_id: UUID, content: str, sequence_number: int
    ) -> BatchMessage:
        """Add a message to a batch."""
        from uuid import uuid4

        batch = await self.get_batch(batch_id)

        if batch.current_size >= batch.max_size:
            from src.modules.batching.exceptions import MessageLimitExceededError

            raise MessageLimitExceededError(
                f"Batch {batch_id} has reached maximum size of {batch.max_size}"
            )

        message = BatchMessage(
            id=uuid4(),
            batch_id=batch_id,
            content=content,
            sequence_number=sequence_number,
        )
        self._session.add(message)

        batch.current_size += 1
        if batch.current_size >= batch.max_size:
            batch.status = "ready"

        await self._session.flush()
        return message

    async def get_batch_messages(self, batch_id: UUID) -> list[BatchMessage]:
        """Get all messages in a batch."""
        result = await self._session.execute(
            select(BatchMessage)
            .where(BatchMessage.batch_id == batch_id)
            .order_by(BatchMessage.sequence_number)
        )
        return list(result.scalars().all())

    async def complete_batch(self, batch_id: UUID) -> None:
        """Mark a batch as completed."""
        batch = await self.get_batch(batch_id)
        batch.status = "completed"
        from datetime import datetime

        batch.completed_at = datetime.utcnow()
        await self._session.flush()

    async def delete_batch(self, batch_id: UUID) -> None:
        """Delete a batch and all its messages."""
        batch = await self.get_batch(batch_id)
        await self._session.delete(batch)
        await self._session.flush()
