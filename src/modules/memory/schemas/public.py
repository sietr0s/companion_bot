"""Публичные HTTP-схемы модуля memory."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConversationCreateRequest(BaseModel):
    user_id: UUID | None = None
    telegram_chat_id: int
    telegram_account_id: UUID | None = None
    status: str = "active"


class ConversationUpdateRequest(BaseModel):
    status: str | None = None
    telegram_chat_id: int | None = None
    telegram_account_id: UUID | None = None
    last_sequence_number: int | None = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None = None
    telegram_chat_id: int
    telegram_account_id: UUID | None = None
    status: str
    last_sequence_number: int
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime


class MessageCreateRequest(BaseModel):
    conversation_id: UUID
    text: str
    direction: str
    message_type: str = "text"
    sequence_number: int
    batch_id: UUID | None = None


class MessageUpdateRequest(BaseModel):
    text: str | None = None
    direction: str | None = None
    message_type: str | None = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    text: str
    direction: str
    message_type: str
    sequence_number: int
    batch_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class SummaryStateCreateRequest(BaseModel):
    conversation_id: UUID
    current_summary: str | None = None
    checkpoint: int = 0


class SummaryStateUpdateRequest(BaseModel):
    current_summary: str | None = None
    checkpoint: int | None = None


class SummaryStateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    current_summary: str | None = None
    checkpoint: int
    created_at: datetime
    updated_at: datetime


class VectorRecordCreateRequest(BaseModel):
    conversation_id: UUID
    text: str
    embedding: list[float] | None = None
    extra_data: dict[str, Any] | None = None


class VectorRecordUpdateRequest(BaseModel):
    text: str | None = None
    embedding: list[float] | None = None
    extra_data: dict[str, Any] | None = None


class VectorRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    text: str
    embedding: list[float] | None = None
    extra_data: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
