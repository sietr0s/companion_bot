"""Схемы событий шины модуля memory."""

from datetime import UTC, datetime

from pydantic import Field

from src.bus.schemas import BaseEvent
from src.core.bus_topics import BusTopics
from src.domain.chat import Batch, ChatRef, ConversationContext, Message, QuotedMessage

__all__ = [
    "QuotedMessage",
    "ChatRef",
    "ConversationContext",
    "ProcessBatchCommand",
    "BuildContextCommand",
    "UpdateMemoryCommand",
    "MaintainMemoryCommand",
    "BatchProcessedEvent",
    "ContextBuiltEvent",
    "MemoryUpdatedEvent",
]


class ProcessBatchCommand(BaseEvent):
    batch: Batch


class BuildContextCommand(ChatRef):
    last_n_messages: int = 50


class UpdateMemoryCommand(ChatRef):
    outgoing_messages: list[str]
    delivery_status: str = "delivered"
    message_type: str = "text"


class MaintainMemoryCommand(ChatRef):
    current_sequence: int = 0


class BatchProcessedEvent(ChatRef, BaseEvent):
    event_name: str = BusTopics.MEMORY_BATCH_PROCESSED


class ContextBuiltEvent(ChatRef, ConversationContext, BaseEvent):
    event_name: str = BusTopics.MEMORY_CONTEXT_BUILT
    retrieved_count: int = 0


class MemoryUpdatedEvent(ChatRef, BaseEvent):
    event_name: str = BusTopics.MEMORY_UPDATED
    messages_count: int
    summary_updated: bool = False
