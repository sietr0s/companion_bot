"""Batching module service. Pipeline state is in-memory only."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from src.core.bus_topics import BusTopics
from src.modules.batching.config import batching_settings
from src.domain.chat import Batch
from src.modules.batching.schemas.events import (
    AddMessageCommand,
    BatchCompletedEvent,
    BatchReadyEvent,
)

if TYPE_CHECKING:
    from src.bus.interface import MessageProducer
    from src.domain.chat import Message


@dataclass
class PendingBatch:
    id: UUID
    channel: str
    chat_id: int
    account_id: UUID
    max_size: int = 1
    messages: list[Message] = field(default_factory=list)


class BatchService:
    """Accumulate messages, wait for more, flush on idle or max_size."""

    def __init__(
        self,
        message_bus: MessageProducer,
        pending: dict[tuple[str, int], PendingBatch] | None = None,
        max_size: int | None = None,
        idle_timeout: float | None = None,
    ) -> None:
        self._message_bus = message_bus
        self._pending = pending if pending is not None else {}
        self._max_size = max_size if max_size is not None else batching_settings.BATCH_MAX_SIZE
        self._idle_timeout = (
            idle_timeout if idle_timeout is not None else batching_settings.BATCH_IDLE_SECONDS
        )
        self._flush_tasks: dict[tuple[str, str, int], asyncio.Task] = {}
        self._locks: dict[tuple[str, str, int], asyncio.Lock] = {}

    @staticmethod
    def _key(channel: str, account_id: UUID, chat_id: int) -> tuple[str, str, int]:
        return (channel, str(account_id), int(chat_id))

    def _lock(self, key: tuple[str, str, int]) -> asyncio.Lock:
        lock = self._locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    def _cancel_wait(self, key: tuple[str, str, int]) -> None:
        task = self._flush_tasks.pop(key, None)
        if task is not None and not task.done():
            task.cancel()

    def _arm_wait(self, key: tuple[str, str, int]) -> None:
        self._cancel_wait(key)
        self._flush_tasks[key] = asyncio.create_task(self._wait_and_flush(key))

    async def _wait_and_flush(self, key: tuple[str, str, int]) -> None:
        try:
            await asyncio.sleep(self._idle_timeout)
        except asyncio.CancelledError:
            return
        async with self._lock(key):
            await self._flush_unlocked(key)

    async def _flush_unlocked(self, key: tuple[str, str, int]) -> BatchReadyEvent | None:
        self._cancel_wait(key)
        pending = self._pending.pop(key, None)
        if pending is None or not pending.messages:
            return None
        batch = Batch(
            id=pending.id,
            channel=pending.channel,
            chat_id=pending.chat_id,
            account_id=pending.account_id,
            messages=pending.messages,
        )
        event = BatchReadyEvent(
            channel=pending.channel,
            chat_id=pending.chat_id,
            account_id=pending.account_id,
            batch=batch,
        )
        await self._message_bus.publish(BusTopics.BATCH_READY, event.model_dump(mode="json"))
        return event

    async def add_incoming_message(self, command: AddMessageCommand) -> BatchReadyEvent | None:
        if command.account_id is None:
            raise ValueError("AddMessageCommand.account_id is required")
        key = self._key(command.channel, command.account_id, command.chat_id)
        async with self._lock(key):
            batch = self._pending.get(key)
            if batch is None:
                batch = PendingBatch(
                    id=uuid4(),
                    channel=command.channel,
                    chat_id=command.chat_id,
                    account_id=command.account_id,
                    max_size=self._max_size,
                )
                self._pending[key] = batch

            batch.messages.append(command.message)
            if len(batch.messages) >= batch.max_size:
                return await self._flush_unlocked(key)

            self._arm_wait(key)
            return None

    async def complete_batch(
        self,
        batch_id: UUID,
        *,
        channel: str,
        chat_id: int,
        account_id: UUID | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        if account_id is not None:
            key = self._key(channel, account_id, chat_id)
            async with self._lock(key):
                self._cancel_wait(key)
                self._pending.pop(key, None)
        event = BatchCompletedEvent(
            batch_id=batch_id,
            channel=channel,
            chat_id=chat_id,
            account_id=account_id,
            success=success,
            error_message=error_message,
        )
        await self._message_bus.publish(BusTopics.BATCH_COMPLETED, event.model_dump(mode="json"))
