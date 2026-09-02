"""Схемы событий шины модуля memory."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.bus.schemas import BaseEvent
from src.core.bus_topics import BusTopics
from src.domain.chat import Message as IncomingMessage
from src.domain.chat import QuotedMessage

__all__ = [
    "IncomingMessage",
    "QuotedMessage",
    "ProcessBatchCommand",
    "BuildContextCommand",
    "UpdateMemoryCommand",
    "BatchProcessedEvent",
    "ContextBuiltEvent",
    "MemoryUpdatedEvent",
]


class ProcessBatchCommand(BaseModel):
    telegram_chat_id: int
    telegram_account_id: UUID | None = None
    conversation_id: UUID | None = None
    messages: list[IncomingMessage]
    direction: str = "incoming"
    batch_id: UUID | None = None


class BuildContextCommand(BaseModel):
    conversation_id: UUID
    telegram_chat_id: int
    telegram_account_id: UUID | None = None
    batch_messages: list[IncomingMessage] = []
    last_n_messages: int = 50


class UpdateMemoryCommand(BaseModel):
    conversation_id: UUID
    telegram_chat_id: int
    outgoing_messages: list[str]
    delivery_status: str = "delivered"


class BatchProcessedEvent(BaseEvent):
    event_name: str = BusTopics.MEMORY_BATCH_PROCESSED
    conversation_id: UUID
    telegram_chat_id: int
    telegram_account_id: UUID | None = None
    sequence_numbers: list[int]
    messages: list[IncomingMessage]
    processed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ContextBuiltEvent(BaseEvent):
    event_name: str = BusTopics.MEMORY_CONTEXT_BUILT
    conversation_id: UUID
    telegram_chat_id: int
    telegram_account_id: UUID | None = None
    context: str
    retrieved_count: int = 0
    built_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MemoryUpdatedEvent(BaseEvent):
    event_name: str = BusTopics.MEMORY_UPDATED
    conversation_id: UUID
    telegram_chat_id: int
    messages_count: int
    summary_updated: bool = False
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
