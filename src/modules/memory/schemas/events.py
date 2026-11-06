"""Схемы событий шины модуля memory."""

from uuid import UUID

from src.bus.schemas import BaseEvent
from src.core.bus_topics import BusTopics
from src.domain.chat import Batch, ChatRef, ConversationContext, QuotedMessage
from src.modules.memory.constants import DEFAULT_LAST_N

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
    conversation_id: UUID
    last_n_messages: int = DEFAULT_LAST_N


class UpdateMemoryCommand(ChatRef):
    conversation_id: UUID
    outgoing_messages: list[str]
    delivery_status: str = "delivered"
    message_type: str = "text"


class MaintainMemoryCommand(ChatRef):
    conversation_id: UUID
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
