"""
Модель профиля пользователя.

User отделён от Auth — это ключевое решение
для Modular Monolith. При выносе модуля users в отдельный
микросервис, профиль полностью независим от авторизации.
"""

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from src.base.model import BaseModel


class User(BaseModel):
    """
    Профиль пользователя.

    auth_id — обычный UUID без ForeignKey.
    Модули не имеют связей на уровне БД — полная изоляция.
    При выносе в микросервис auth_id остаётся идентификатором
    пользователя из сервиса авторизации.
    """

    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    # Обычный UUID — без ForeignKey к auth.
    # Модули изолированы: каждый может работать в отдельной БД.
    auth_id: Mapped[uuid.UUID] = mapped_column(
        unique=True,
        index=True,
        nullable=False,
    )
    first_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    last_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Foreign key к таблице telegram — связь один-к-одному
    telegram_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("telegram.id"), nullable=True
    )
    # Relationship к модели Telegram
    telegram: Mapped["Telegram | None"] = relationship(
        "Telegram", back_populates="user", uselist=False
    )


class Telegram(BaseModel):
    """
    Модель Telegram-аккаунта.

    Хранит данные Telegram: telegram_id, username, имена.
    На неё ссылается User через foreign key.
    """

    __tablename__ = "telegram"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    telegram_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    telegram_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    telegram_first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    telegram_last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user: Mapped["User | None"] = relationship("User", back_populates="telegram", uselist=False)
