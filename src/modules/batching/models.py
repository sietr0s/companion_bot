"""Batching module database models."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.base.model import BaseModel


class Batch(BaseModel):
    """Unused table: runtime batching is in-memory. Kept for schema hygiene."""

    __tablename__ = "batches"

    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="telegram")
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    account_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    max_size: Mapped[int] = mapped_column(Integer, default=1)
    current_size: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list["BatchMessage"]] = relationship(
        "BatchMessage", back_populates="batch", cascade="all, delete-orphan"
    )


class BatchMessage(BaseModel):
    """Message belonging to a batch."""

    __tablename__ = "batch_messages"

    batch_id: Mapped[UUID] = mapped_column(ForeignKey("batches.id"), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    batch: Mapped["Batch"] = relationship("Batch", back_populates="messages")
