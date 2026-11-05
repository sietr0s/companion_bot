"""Состояние оркестратора (не HTTP и не событие шины)."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.chat import Batch, ChatRef, ConversationContext


class OrchestratorState(BaseModel):
    correlation_id: UUID
    chat: ChatRef
    memory: ConversationContext = Field(default_factory=ConversationContext)
    reply_messages: list[str] = Field(default_factory=list)
    batch_messages: Batch | None = None
    delivery_report: dict | None = None
    asked_voice: int = 0
    pending_outgoing_texts: list[str] = Field(default_factory=list)
    pending_delivery: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
