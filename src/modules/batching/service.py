"""Batching module service."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.base.service import BaseService
from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.modules.batching.exceptions import MessageLimitExceededError
from src.modules.batching.models import Batch, BatchMessage
from src.modules.batching.repository import BatchMessageRepository, BatchRepository
from src.modules.batching.schemas.events import (
    AddMessageCommand,
    BatchCompletedEvent,
    BatchReadyEvent,
)


class BatchService(BaseService[BatchRepository, Batch]):
    def __init__(
        self,
        repository: BatchRepository,
        message_bus: MessageProducer,
        message_repository: BatchMessageRepository | None = None,
    ) -> None:
        super().__init__(repository)
        self._message_bus = message_bus
        self._messages = message_repository or BatchMessageRepository()

    async def add_incoming_message(
        self, session: AsyncSession, command: AddMessageCommand
    ) -> BatchReadyEvent | None:
        batch = await self.repository.get_pending_batch(session, command.telegram_chat_id)
        if batch is None:
            batch = await self.repository.create(
                session,
                {
                    "telegram_chat_id": command.telegram_chat_id,
                    "telegram_account_id": command.telegram_account_id,
                    "max_size": 1,
                    "current_size": 0,
                    "status": "pending",
                },
            )

        if batch.current_size >= batch.max_size:
            raise MessageLimitExceededError(
                f"Batch {batch.id} has reached maximum size of {batch.max_size}"
            )

        sequence = (
            command.sequence_number if command.sequence_number is not None else batch.current_size + 1
        )
        await self._messages.create(
            session,
            {
                "batch_id": batch.id,
                "content": command.content,
                "sequence_number": sequence,
            },
        )

        new_size = batch.current_size + 1
        status = "ready" if new_size >= batch.max_size else batch.status
        batch = await self.repository.update(
            session,
            batch,
            {"current_size": new_size, "status": status},
        )
        if batch.status != "ready":
            return None

        messages = await self._messages.get_by_batch_id(session, batch.id)
        event = BatchReadyEvent(
            batch_id=batch.id,
            telegram_chat_id=batch.telegram_chat_id,
            telegram_account_id=batch.telegram_account_id,
            messages=[msg.content for msg in messages],
            message_count=len(messages),
        )
        await self._message_bus.publish(BusTopics.BATCH_READY, event.to_bus_dict())
        return event

    async def complete_batch(
        self,
        session: AsyncSession,
        batch: Batch,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        await self.repository.update(
            session,
            batch,
            {"status": "completed", "completed_at": datetime.now(UTC)},
        )
        event = BatchCompletedEvent(
            batch_id=batch.id,
            telegram_chat_id=batch.telegram_chat_id,
            success=success,
            error_message=error_message,
        )
        await self._message_bus.publish(BusTopics.BATCH_COMPLETED, event.to_bus_dict())


class BatchMessageService(BaseService[BatchMessageRepository, BatchMessage]):
    def __init__(self, repository: BatchMessageRepository) -> None:
        super().__init__(repository)
