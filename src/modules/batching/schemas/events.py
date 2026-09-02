"""Схемы событий шины модуля batching."""

from uuid import UUID

from pydantic import BaseModel, Field

from src.bus.schemas import BaseEvent
from src.core.bus_topics import BusTopics
from src.domain.chat import Message


class AddMessageCommand(BaseModel):
    telegram_chat_id: int
    telegram_account_id: UUID
    message: Message
    sequence_number: int | None = None


class BatchReadyEvent(BaseEvent):
    event_name: str = BusTopics.BATCH_READY
    batch_id: UUID
    telegram_chat_id: int
    telegram_account_id: UUID
    messages: list[Message] = Field(default_factory=list)
    message_count: int = 0


class BatchCompletedEvent(BaseEvent):
    event_name: str = BusTopics.BATCH_COMPLETED
    batch_id: UUID
    telegram_chat_id: int
    success: bool
    error_message: str | None = None
