"""
Модуль Telegram-клиентов.

Модуль для подключения к Telegram через Telethon, чтения сообщений
и управления настройками чтения.
"""

import uuid

from sqlalchemy import JSON, BigInteger, Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.base.model import BaseModel


class TelegramAccount(BaseModel):
    """
    Telegram-аккаунт пользователя.

    session_file — путь к SQLite session-файлу Telethon.
    is_connected — отражает состояния подключения (может устареть).
    """

    __tablename__ = "telegram_account"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    telegram_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    phone: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    session_file: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    is_connected: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
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
    username: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )


class TelegramSettings(BaseModel):
    """
    Настройки чтения Telegram-аккаунта.

    Определяет какие чаты читать и из каких списков.
    Привязан к TelegramAccount через account_id с cascade delete.
    """

    __tablename__ = "telegram_settings"

    # account_id — связь с TelegramAccount (cascade delete)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("telegram_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Читать группы и каналы
    read_groups: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    # Читать личные сообщения
    read_personal: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    # Читать каналы
    read_channels: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    # Whitelist конкретных chat_id (если пустой — читать все разрешённых типов)
    whitelist_chat_ids: Mapped[list | None] = mapped_column(
        JSON,
        default=list,
        nullable=True,
    )


class TelegramChatState(BaseModel):
    """
    Состояние чтения чата Telegram.

    Хранит ID последнего прочитанного сообщения для пары (account_id, chat_id).
    Используется для отслеживания прогресса чтения сообщений.
    """

    __tablename__ = "telegram_chat_state"

    # Связь с TelegramAccount (cascade delete)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("telegram_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # ID чата в Telegram
    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
    # ID последнего прочитанного сообщения
    last_read_message_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    # Уникальность пары (account_id, chat_id)
    __table_args__ = (
        UniqueConstraint("account_id", "chat_id", name="uq_telegram_chat_state_account_chat"),
    )
