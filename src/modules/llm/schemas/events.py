"""Схемы событий шины модуля llm."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.bus.schemas import BaseEvent
from src.core.bus_topics import BusTopics
from src.domain.chat import Batch, Message


class GenerateReplyCommand(BaseModel):
    conversation_id: UUID
    telegram_chat_id: int
    telegram_account_id: UUID | None = None
    context: str
    persona: str = "default"


class SummarizeCommand(BaseModel):
    conversation_id: UUID
    messages: list[str]
    max_chars: int = 1000


class ReplyGeneratedEvent(BaseEvent):
    event_name: str = BusTopics.LLM_REPLY_GENERATED
    conversation_id: UUID
    telegram_chat_id: int
    telegram_account_id: UUID | None = None
    messages: list[Message]
    batch: Batch | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReplySuppressedEvent(BaseEvent):
    event_name: str = BusTopics.LLM_REPLY_SUPPRESSED
    conversation_id: UUID
    telegram_chat_id: int
    telegram_account_id: UUID | None = None
    reason: str = "no_response_needed"
    suppressed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SummaryGeneratedEvent(BaseEvent):
    event_name: str = BusTopics.LLM_SUMMARY_GENERATED
    conversation_id: UUID
    summary: str
    char_count: int
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
