"""Memory module SQLAlchemy models."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.base.model import BaseModel
from src.modules.memory.constants import EMBEDDING_DIM
from src.modules.memory.embedding_type import EmbeddingVector


class Conversation(BaseModel):
    """Conversation history for one companion chat on a channel."""

    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint(
            "channel",
            "account_id",
            "chat_id",
            name="uq_conversations_channel_account_chat",
        ),
    )

    user_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="telegram")
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    account_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    last_sequence_number: Mapped[int] = mapped_column(Integer, default=0)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    message_batches: Mapped[list["MessageBatch"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    summary_state: Mapped["SummaryState | None"] = relationship(
        back_populates="conversation", uselist=False, cascade="all, delete-orphan"
    )
    vector_records: Mapped[list["VectorRecord"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class MessageBatch(BaseModel):
    """Persisted same-role flush (incoming debounce or outgoing send)."""

    __tablename__ = "message_batches"

    conversation_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("conversations.id"), nullable=False
    )
    direction: Mapped[str] = mapped_column(String(10), nullable=False)

    conversation: Mapped["Conversation"] = relationship(back_populates="message_batches")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )


class Message(BaseModel):
    """Single message in a conversation."""

    __tablename__ = "messages"

    conversation_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("conversations.id"), nullable=False
    )
    batch_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("message_batches.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), default="text")
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    batch: Mapped["MessageBatch"] = relationship(back_populates="messages")

    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "sequence_number",
            name="uq_messages_conversation_seq",
        ),
    )


class SummaryState(BaseModel):
    """Rolling summary for a conversation."""

    __tablename__ = "summary_states"

    conversation_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("conversations.id"), unique=True, nullable=False
    )
    current_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    checkpoint: Mapped[int] = mapped_column(Integer, default=0)
    cluster_checkpoint: Mapped[int] = mapped_column(Integer, default=0)

    conversation: Mapped["Conversation"] = relationship(back_populates="summary_state")


class VectorRecord(BaseModel):
    """Topic/reference embedding. Messages live on the conversation, not in the vector."""

    __tablename__ = "vector_records"

    conversation_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("conversations.id"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), default="topic", nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        EmbeddingVector(EMBEDDING_DIM), nullable=True
    )
    seq_from: Mapped[int] = mapped_column(Integer, nullable=False)
    seq_to: Mapped[int] = mapped_column(Integer, nullable=False)
    partial: Mapped[bool] = mapped_column(default=False, nullable=False)

    conversation: Mapped["Conversation"] = relationship(back_populates="vector_records")
