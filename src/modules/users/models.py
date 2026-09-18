"""Собеседник на канале (telegram / instagram)."""

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.base.model import BaseModel


class User(BaseModel):
    """
    Человек, с которым общаются подключённые клиенты.

    Не связан с auth: auth — только админы панели.
    notes — свободные подсказки для нейросети.
    """

    __tablename__ = "user"
    __table_args__ = (
        UniqueConstraint("platform", "platform_user_id", name="uq_user_platform_user_id"),
    )

    platform: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    platform_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
