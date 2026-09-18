"""Схемы событий шины модуля batching."""

from uuid import UUID

from pydantic import Field

from src.bus.schemas import BaseEvent
from src.core.bus_topics import BusTopics
from src.domain.chat import Batch, ChatRef, Message


class AddMessageCommand(ChatRef):
    message: Message
    sequence_number: int | None = None


class BatchReadyEvent(ChatRef, BaseEvent):
    event_name: str = BusTopics.BATCH_READY
    batch: Batch


class BatchCompletedEvent(ChatRef, BaseEvent):
    event_name: str = BusTopics.BATCH_COMPLETED
    batch_id: UUID
    success: bool
    error_message: str | None = None
