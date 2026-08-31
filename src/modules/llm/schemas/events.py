"""Схемы событий шины модуля llm."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.bus_topics import BusTopics


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


class ReplyGeneratedEvent(BaseModel):
    conversation_id: UUID
    telegram_chat_id: int
    telegram_account_id: UUID | None = None
    messages: list[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_bus_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["event_name"] = BusTopics.LLM_REPLY_GENERATED
        return data


class ReplySuppressedEvent(BaseModel):
    conversation_id: UUID
    telegram_chat_id: int
    telegram_account_id: UUID | None = None
    reason: str = "no_response_needed"
    suppressed_at: datetime = Field(default_factory=datetime.utcnow)

    def to_bus_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["event_name"] = BusTopics.LLM_REPLY_SUPPRESSED
        return data


class SummaryGeneratedEvent(BaseModel):
    conversation_id: UUID
    summary: str
    char_count: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_bus_dict(self) -> dict:
        data = self.model_dump(mode="json")
        data["event_name"] = BusTopics.LLM_SUMMARY_GENERATED
        return data
