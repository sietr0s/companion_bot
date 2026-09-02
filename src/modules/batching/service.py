"""Batching module service. Pipeline state is in-memory only."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from uuid import UUID, uuid4

from src.bus.interface import MessageProducer
from src.core.bus_topics import BusTopics
from src.core.config import settings
from src.domain.chat import Message
from src.modules.batching.schemas.events import (
    AddMessageCommand,
    BatchCompletedEvent,
    BatchReadyEvent,
)


@dataclass
class PendingBatch:
    id: UUID
    telegram_chat_id: int
    telegram_account_id: UUID
    max_size: int = 1
    messages: list[Message] = field(default_factory=list)


class BatchService:
    """Accumulate messages, wait for more, flush on idle or max_size."""

    def __init__(
        self,
        message_bus: MessageProducer,
        pending: dict[int, PendingBatch] | None = None,
        max_size: int | None = None,
        idle_timeout: float | None = None,
    ) -> None:
        self._message_bus = message_bus
        self._pending = pending if pending is not None else {}
        self._max_size = max_size if max_size is not None else settings.BATCH_MAX_SIZE
        self._idle_timeout = (
            idle_timeout if idle_timeout is not None else settings.BATCH_IDLE_SECONDS
        )
        self._flush_tasks: dict[int, asyncio.Task] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    def _lock(self, chat_id: int) -> asyncio.Lock:
        lock = self._locks.get(chat_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[chat_id] = lock
        return lock

    def _cancel_wait(self, chat_id: int) -> None:
        task = self._flush_tasks.pop(chat_id, None)
        if task is not None and not task.done():
            task.cancel()

    def _arm_wait(self, chat_id: int) -> None:
        self._cancel_wait(chat_id)
        self._flush_tasks[chat_id] = asyncio.create_task(self._wait_and_flush(chat_id))

    async def _wait_and_flush(self, chat_id: int) -> None:
        try:
            await asyncio.sleep(self._idle_timeout)
        except asyncio.CancelledError:
            return
        async with self._lock(chat_id):
            await self._flush_unlocked(chat_id)

    async def _flush_unlocked(self, chat_id: int) -> BatchReadyEvent | None:
        self._cancel_wait(chat_id)
        batch = self._pending.pop(chat_id, None)
        if batch is None or not batch.messages:
            return None
        event = BatchReadyEvent(
            batch_id=batch.id,
            telegram_chat_id=batch.telegram_chat_id,
            telegram_account_id=batch.telegram_account_id,
            messages=list(batch.messages),
            message_count=len(batch.messages),
        )
        await self._message_bus.publish(BusTopics.BATCH_READY, event.to_bus_dict())
        return event

    async def add_incoming_message(self, command: AddMessageCommand) -> BatchReadyEvent | None:
        chat_id = command.telegram_chat_id
        async with self._lock(chat_id):
            batch = self._pending.get(chat_id)
            if batch is None:
                batch = PendingBatch(
                    id=uuid4(),
                    telegram_chat_id=chat_id,
                    telegram_account_id=command.telegram_account_id,
                    max_size=self._max_size,
                )
                self._pending[chat_id] = batch

            batch.messages.append(command.message)
            if len(batch.messages) >= batch.max_size:
                return await self._flush_unlocked(chat_id)

            self._arm_wait(chat_id)
            return None

    async def complete_batch(
        self,
        batch_id: UUID,
        telegram_chat_id: int,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        async with self._lock(telegram_chat_id):
            self._cancel_wait(telegram_chat_id)
            self._pending.pop(telegram_chat_id, None)
        event = BatchCompletedEvent(
            batch_id=batch_id,
            telegram_chat_id=telegram_chat_id,
            success=success,
            error_message=error_message,
        )
        await self._message_bus.publish(BusTopics.BATCH_COMPLETED, event.to_bus_dict())
