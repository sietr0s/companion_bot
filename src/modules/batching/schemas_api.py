"""Batching module API schemas (HTTP)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BatchResponse(BaseModel):
    """Response schema for batch operations."""

    id: UUID
    user_id: UUID
    status: str
    max_size: int
    current_size: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class BatchMessageResponse(BaseModel):
    """Response schema for batch message."""

    id: UUID
    batch_id: UUID
    content: str
    sequence_number: int
    created_at: datetime


class CreateBatchRequest(BaseModel):
    """Request schema for creating a batch."""

    user_id: UUID
    max_size: int = Field(default=10, ge=1, le=100)


class AddMessageRequest(BaseModel):
    """Request schema for adding a message to batch."""

    content: str = Field(..., min_length=1, max_length=10000)
