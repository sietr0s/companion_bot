"""Memory module SQLAlchemy models."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.base.model import BaseModel
from src.modules.memory.constants import EMBEDDING_DIM
from src.modules.memory.embedding_type import EmbeddingVector


class Conversation(BaseModel):
    """Conversation history for a Telegram chat."""

    __tablename__ = "conversations"

    user_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    telegram_account_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    last_sequence_number: Mapped[int] = mapped_column(Integer, default=0)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    summary_state: Mapped["SummaryState | None"] = relationship(
        back_populates="conversation", uselist=False, cascade="all, delete-orphan"
    )
    vector_records: Mapped[list["VectorRecord"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(BaseModel):
    """Single message in a conversation."""

    __tablename__ = "messages"

    conversation_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("conversations.id"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), default="text")
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    batch_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class SummaryState(BaseModel):
    """Rolling summary for a conversation."""

    __tablename__ = "summary_states"

    conversation_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("conversations.id"), unique=True, nullable=False
    )
    current_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    checkpoint: Mapped[int] = mapped_column(Integer, default=0)

    conversation: Mapped["Conversation"] = relationship(back_populates="summary_state")


class VectorRecord(BaseModel):
    """Optional embedding record for semantic search."""

    __tablename__ = "vector_records"

    conversation_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("conversations.id"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        EmbeddingVector(EMBEDDING_DIM), nullable=True
    )
    extra_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    conversation: Mapped["Conversation"] = relationship(back_populates="vector_records")
