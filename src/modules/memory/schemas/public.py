"""Публичные HTTP-схемы модуля memory."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConversationCreate(BaseModel):
    user_id: UUID | None = None
    channel: str = "telegram"
    chat_id: int
    account_id: UUID | None = None
    status: str = "active"


class ConversationUpdate(BaseModel):
    status: str | None = None
    channel: str | None = None
    chat_id: int | None = None
    account_id: UUID | None = None
    last_sequence_number: int | None = None


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None = None
    channel: str
    chat_id: int
    account_id: UUID | None = None
    status: str
    last_sequence_number: int
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime


class MemoryMessageCreate(BaseModel):
    conversation_id: UUID
    text: str
    direction: str
    message_type: str = "text"
    sequence_number: int
    batch_id: UUID | None = None


class MemoryMessageUpdate(BaseModel):
    text: str | None = None
    direction: str | None = None
    message_type: str | None = None


class MemoryMessageRead(BaseModel):
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


class SummaryStateCreate(BaseModel):
    conversation_id: UUID
    current_summary: str | None = None
    checkpoint: int = 0


class SummaryStateUpdate(BaseModel):
    current_summary: str | None = None
    checkpoint: int | None = None


class SummaryStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    current_summary: str | None = None
    checkpoint: int
    created_at: datetime
    updated_at: datetime


class VectorRecordCreate(BaseModel):
    conversation_id: UUID
    text: str
    kind: str = "topic"
    embedding: list[float] | None = None
    seq_from: int = 0
    seq_to: int = 0
    partial: bool = False


class VectorRecordUpdate(BaseModel):
    text: str | None = None
    kind: str | None = None
    embedding: list[float] | None = None
    seq_from: int | None = None
    seq_to: int | None = None
    partial: bool | None = None


class VectorRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    text: str
    kind: str = "topic"
    embedding: list[float] | None = None
    seq_from: int
    seq_to: int
    partial: bool = False
    created_at: datetime
    updated_at: datetime


class VectorTopicRead(BaseModel):
    id: UUID
    conversation_id: UUID
    title: str
    seq_from: int
    seq_to: int
    message_count: int
    kind: str = "topic"
    partial: bool = False
    created_at: datetime


class VectorTopicDetailRead(VectorTopicRead):
    messages: list[MemoryMessageRead] = []
