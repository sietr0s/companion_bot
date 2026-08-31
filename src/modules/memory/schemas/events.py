"""Схемы событий шины модуля memory."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.bus_topics import BusTopics


class ProcessBatchCommand(BaseModel):
    telegram_chat_id: int
    telegram_account_id: UUID | None = None
    conversation_id: UUID | None = None
    messages: list[str]
    direction: str = "incoming"
    message_type: str = "text"
    batch_id: UUID | None = None


class BuildContextCommand(BaseModel):
    conversation_id: UUID
    telegram_chat_id: int
    telegram_account_id: UUID | None = None
    last_n_messages: int = 50


class UpdateMemoryCommand(BaseModel):
    conversation_id: UUID
    telegram_chat_id: int
    outgoing_messages: list[str]
    delivery_status: str = "delivered"


class BatchProcessedEvent(BaseModel):
    conversation_id: UUID
    telegram_chat_id: int
    telegram_account_id: UUID | None = None
    sequence_numbers: list[int]
    messages: list[str]
    processed_at: datetime = Field(default_factory=datetime.utcnow)

    def to_bus_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["event_name"] = BusTopics.MEMORY_BATCH_PROCESSED
        return data


class ContextBuiltEvent(BaseModel):
    conversation_id: UUID
    telegram_chat_id: int
    telegram_account_id: UUID | None = None
    context: str
    retrieved_count: int = 0
    built_at: datetime = Field(default_factory=datetime.utcnow)

    def to_bus_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["event_name"] = BusTopics.MEMORY_CONTEXT_BUILT
        return data


class MemoryUpdatedEvent(BaseModel):
    conversation_id: UUID
    telegram_chat_id: int
    messages_count: int
    summary_updated: bool = False
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_bus_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["event_name"] = BusTopics.MEMORY_UPDATED
        return data
