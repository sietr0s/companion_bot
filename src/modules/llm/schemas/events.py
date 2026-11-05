"""Схемы событий шины модуля llm."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.bus.schemas import BaseEvent
from src.core.bus_topics import BusTopics
from src.domain.chat import Batch, ChatRef, ConversationContext, Message


class GenerateReplyCommand(ChatRef, ConversationContext):
    """Generate a reply from structured, channel-independent memory."""

    conversation_id: UUID


class SummarizeCommand(BaseModel):
    conversation_id: UUID
    messages: list[str]
    max_chars: int = 1000


class ReplyGeneratedEvent(ChatRef, BaseEvent):
    event_name: str = BusTopics.LLM_REPLY_GENERATED
    conversation_id: UUID
    messages: list[Message]
    batch: Batch | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReplySuppressedEvent(ChatRef, BaseEvent):
    event_name: str = BusTopics.LLM_REPLY_SUPPRESSED
    conversation_id: UUID
    reason: str = "no_response_needed"
    suppressed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SummaryGeneratedEvent(BaseEvent):
    event_name: str = BusTopics.LLM_SUMMARY_GENERATED
    conversation_id: UUID
    summary: str
    char_count: int
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
