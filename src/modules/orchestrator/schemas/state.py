"""Состояние оркестратора (не HTTP и не событие шины)."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OrchestratorState(BaseModel):
    correlation_id: UUID
    telegram_account_id: UUID | None = None
    telegram_chat_id: int | None = None
    current_message: str | None = None
    conversation_id: UUID | None = None
    context: str | None = None
    reply_messages: list[str] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
