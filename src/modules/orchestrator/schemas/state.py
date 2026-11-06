"""Состояние оркестратора (не HTTP и не событие шины)."""

from pydantic import BaseModel, Field

from src.domain.chat import Batch, ChatRef, ConversationContext


class OrchestratorState(BaseModel):
    chat: ChatRef
    memory: ConversationContext = Field(default_factory=ConversationContext)
    reply_messages: list[str] = Field(default_factory=list)
    batch_messages: Batch | None = None
    delivery_report: dict | None = None
    asked_voice: int = 0
    pending_outgoing_texts: list[str] = Field(default_factory=list)
