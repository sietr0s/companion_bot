"""
Модели модуля нотификаций.

NotificationTemplate — Jinja2-шаблоны (БД).
NotificationLog — история отправленных уведомлений.
"""

import uuid

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.base.model import BaseModel


class NotificationTemplate(BaseModel):
    """
    Шаблон уведомления.

    name — уникальное имя (welcome, password_reset и т.д.).
    channel — канал доставки (email, sms).
    subject_template — Jinja2-шаблон темы (для email).
    body_template — Jinja2-шаблон тела.
    """

    __tablename__ = "notification_template"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    subject_template: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    body_template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )


class NotificationLog(BaseModel):
    """
    Лог отправленного уведомления.

    Позволяет отслеживать статус, отлаживать ошибки,
    показывать историю пользователю.
    """

    __tablename__ = "notification_log"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    auth_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    template_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    recipient: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    subject: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
