"""Публичные HTTP-схемы модуля batching."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BatchCreate(BaseModel):
    telegram_chat_id: int
    telegram_account_id: UUID
    max_size: int = Field(default=1, ge=1, le=100)
    status: str = "pending"
    current_size: int = 0


class BatchUpdate(BaseModel):
    status: str | None = None
    max_size: int | None = None
    current_size: int | None = None
    completed_at: datetime | None = None


class BatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    telegram_chat_id: int
    telegram_account_id: UUID
    status: str
    max_size: int
    current_size: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class BatchMessageCreate(BaseModel):
    batch_id: UUID
    content: str = Field(..., min_length=1)
    sequence_number: int


class BatchMessageUpdate(BaseModel):
    content: str | None = None
    sequence_number: int | None = None


class BatchMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    batch_id: UUID
    content: str
    sequence_number: int
    created_at: datetime
    updated_at: datetime
