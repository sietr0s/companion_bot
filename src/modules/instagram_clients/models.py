"""ORM for Instagram accounts, read settings, and Direct cursors."""

import uuid

from sqlalchemy import JSON, BigInteger, Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.base.model import BaseModel


class InstagramAccount(BaseModel):
    """Instagram account. session_file is instagrapi settings JSON. Password is never stored."""

    __tablename__ = "instagram_account"

    username: Mapped[str] = mapped_column(String(100), nullable=False)
    instagram_pk: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    session_file: Mapped[str] = mapped_column(String(500), nullable=False)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)


class InstagramSettings(BaseModel):
    """Read settings for an Instagram account. Empty whitelist + use_whitelist = nobody."""

    __tablename__ = "instagram_settings"

    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instagram_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    use_whitelist: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    whitelist_user_pks: Mapped[list | None] = mapped_column(JSON, default=list, nullable=True)


class InstagramChatState(BaseModel):
    """Last seen Direct item per (account, thread). last_item_id is a string (not always int)."""

    __tablename__ = "instagram_chat_state"
    __table_args__ = (
        UniqueConstraint("account_id", "thread_id", name="uq_instagram_chat_state_account_thread"),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instagram_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    thread_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    last_item_id: Mapped[str] = mapped_column(String(64), nullable=False)
