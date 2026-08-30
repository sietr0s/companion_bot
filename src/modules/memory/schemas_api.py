"""Memory module API schemas (HTTP requests/responses)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


# Request schemas
class ConversationCreateRequest(BaseModel):
    """Request to create a conversation."""

    user_id: UUID
    telegram_chat_id: int


class ConversationUpdateRequest(BaseModel):
    """Request to update a conversation."""

    status: str | None = None
    telegram_chat_id: int | None = None


# Response schemas
class ConversationResponse(BaseModel):
    """Conversation response schema."""

    id: UUID
    user_id: UUID
    telegram_chat_id: int
    status: str
    last_sequence_number: int
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Message response schema."""

    id: UUID
    conversation_id: UUID
    text: str
    direction: str
    message_type: str
    sequence_number: int
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """List of conversations response."""

    conversations: list[ConversationResponse]
    total: int
