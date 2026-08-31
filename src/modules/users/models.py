"""Собеседник, который пишет через telegram_clients."""

from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.base.model import BaseModel


class User(BaseModel):
    """
    Человек в Telegram, с которым общаются подключённые клиенты.

    Не связан с auth: auth — только админы панели.
    notes — свободные подсказки для нейросети (расширим позже).
    """

    __tablename__ = "user"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
