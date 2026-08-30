"""Batching module bus schemas (events and commands)."""

from uuid import UUID

from pydantic import BaseModel


class AddMessageCommand(BaseModel):
    """Command to add a message to a batch."""

    batch_id: UUID
    content: str
    sequence_number: int


class BatchReadyEvent(BaseModel):
    """Event published when a batch is ready for processing."""

    batch_id: UUID
    user_id: UUID
    message_count: int
    message_ids: list[UUID]


class BatchCompletedEvent(BaseModel):
    """Event published when a batch processing is completed."""

    batch_id: UUID
    user_id: UUID
    success: bool
    error_message: str | None = None
