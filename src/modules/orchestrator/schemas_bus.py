"""Orchestrator module bus schemas (internal state tracking)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# Internal state schemas (not published, used for correlation)
class OrchestratorState(BaseModel):
    """State tracked by orchestrator for a correlation ID."""

    correlation_id: UUID
    current_message: str | None = None
    current_batch: list[str] | None = None
    user_id: UUID | None = None
    batch_processed: bool = False
    context: str | None = None
    reply_messages: list[str] | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Commands that orchestrator publishes to other modules
class AddMessageToBatchCommand(BaseModel):
    """Command to add message to batching module."""

    telegram_chat_id: int
    message_text: str
    message_id: int | None = None


class GetUserCommand(BaseModel):
    """Command to get or create user."""

    telegram_chat_id: int


class ProcessBatchCommand(BaseModel):
    """Command to process batch in memory module."""

    conversation_id: UUID
    telegram_chat_id: int
    messages: list[str]
    batch_id: UUID | None = None


class BuildContextCommand(BaseModel):
    """Command to build context in memory module."""

    conversation_id: UUID
    telegram_chat_id: int
    last_n_messages: int = 50


class GenerateReplyCommand(BaseModel):
    """Command to generate reply in LLM module."""

    conversation_id: UUID
    telegram_chat_id: int
    context: str


class SendMessageCommand(BaseModel):
    """Command to send message via telegram_clients."""

    telegram_account_id: UUID | None = None
    chat_id: int
    text: str
    reply_to_message_id: int | None = None


class UpdateMemoryCommand(BaseModel):
    """Command to update memory after delivery."""

    conversation_id: UUID
    telegram_chat_id: int
    outgoing_messages: list[str]
    delivery_status: str = "delivered"
