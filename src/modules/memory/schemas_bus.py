"""Memory module bus schemas (commands and events)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# Commands (incoming to memory.in)
class ProcessBatchCommand(BaseModel):
    """Command to process a batch of messages."""

    conversation_id: UUID
    telegram_chat_id: int
    messages: list[str]
    direction: str = "incoming"
    message_type: str = "text"
    batch_id: UUID | None = None


class BuildContextCommand(BaseModel):
    """Command to build context for LLM."""

    conversation_id: UUID
    telegram_chat_id: int
    last_n_messages: int = 50


class UpdateMemoryCommand(BaseModel):
    """Command to update memory after message delivery."""

    conversation_id: UUID
    telegram_chat_id: int
    outgoing_messages: list[str]
    delivery_status: str = "delivered"


# Events (outgoing from memory.out)
class BatchProcessedEvent(BaseModel):
    """Event published when batch is processed."""

    conversation_id: UUID
    telegram_chat_id: int
    sequence_numbers: list[int]
    processed_at: datetime = Field(default_factory=datetime.utcnow)


class ContextBuiltEvent(BaseModel):
    """Event published when context is built."""

    conversation_id: UUID
    telegram_chat_id: int
    context: str
    retrieved_count: int = 0
    built_at: datetime = Field(default_factory=datetime.utcnow)


class MemoryUpdatedEvent(BaseModel):
    """Event published when memory is updated."""

    conversation_id: UUID
    telegram_chat_id: int
    messages_count: int
    summary_updated: bool = False
    updated_at: datetime = Field(default_factory=datetime.utcnow)
