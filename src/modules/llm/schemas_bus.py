"""LLM module bus schemas (commands and events)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# Commands (incoming to llm.in)
class GenerateReplyCommand(BaseModel):
    """Command to generate a reply."""

    conversation_id: UUID
    telegram_chat_id: int
    context: str
    persona: str = "default"


class SummarizeCommand(BaseModel):
    """Command to summarize conversation."""

    conversation_id: UUID
    messages: list[str]
    max_chars: int = 1000


class PreRetrieveCommand(BaseModel):
    """Command to generate search query for RAG."""

    conversation_id: UUID
    context: str


class PostRetrieveCommand(BaseModel):
    """Command to re-rank retrieved candidates."""

    conversation_id: UUID
    query: str
    candidates: list[str]
    top_k: int = 3


# Events (outgoing from llm.out)
class ReplyGeneratedEvent(BaseModel):
    """Event published when reply is generated."""

    conversation_id: UUID
    telegram_chat_id: int
    messages: list[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ReplySuppressedEvent(BaseModel):
    """Event published when reply is suppressed (decided not to respond)."""

    conversation_id: UUID
    telegram_chat_id: int
    reason: str = "no_response_needed"
    suppressed_at: datetime = Field(default_factory=datetime.utcnow)


class SummaryGeneratedEvent(BaseModel):
    """Event published when summary is generated."""

    conversation_id: UUID
    summary: str
    char_count: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class PreRetrieveResultEvent(BaseModel):
    """Event published with search query for RAG."""

    conversation_id: UUID
    search_query: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class PostRetrieveResultEvent(BaseModel):
    """Event published with re-ranked candidates."""

    conversation_id: UUID
    selected_candidates: list[str]
    total_candidates: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)
