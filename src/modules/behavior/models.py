"""Persisted agent life and per-chat delivery streak."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.base.model import Base, BaseModel


class BehaviorAccountState(Base):
    __tablename__ = "behavior_account_state"

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("telegram_account.id", ondelete="CASCADE"),
        primary_key=True,
    )
    activity: Mapped[str] = mapped_column(String(32), default="working", nullable=False)
    mood: Mapped[str] = mapped_column(String(32), default="neutral", nullable=False)
    activity_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BehaviorChatState(BaseModel):
    __tablename__ = "behavior_chat_state"

    account_id: Mapped[UUID] = mapped_column(
        ForeignKey("telegram_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    consecutive_voice_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_delivery: Mapped[str | None] = mapped_column(String(16), nullable=True)

    __table_args__ = (
        UniqueConstraint("account_id", "chat_id", name="uq_behavior_chat_state_account_chat"),
    )
