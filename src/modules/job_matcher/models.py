"""
Модели модуля job_matcher.

Subscription — подписка пользователя на определённые типы офферов.
JobOffer — предложение о работе (спарсено из Telegram-группы).
"""

import uuid

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON, Uuid

from src.base.model import BaseModel


class Subscription(BaseModel):
    """
    Подписка пользователя на предложения о работе.

    Привязана к Auth через auth_id — без ForeignKey.
    Модули изолированы: при выносе в микросервис
    auth_id остаётся идентификатором из сервиса авторизации.
    """

    __tablename__ = "subscriptions"

    auth_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
        comment="ID из сервиса авторизации (Auth.id)",
    )
    keywords: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Ключевые слова для поиска (Python, Java, Go)",
    )
    category_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="ID категорий из classifier (backend, frontend, devops, data_science)",
    )
    min_salary: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Минимальная зарплата",
    )
    max_salary: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Максимальная зарплата",
    )
    locations: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Города (Москва, СПб, удалёнка)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Подписка активна",
    )


class JobOffer(BaseModel):
    """
    Предложение о работе, спарсенное из Telegram-группы.

    Содержит сырые данные — title, description, tags.
    После классификации отправляется в notifier для рендера.
    """

    __tablename__ = "job_offers"

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Заголовок вакансии",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Описание вакансии",
    )
    tags: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Теги (Python, backend, senior)",
    )
    salary_from: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Зарплата от",
    )
    salary_to: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Зарплата до",
    )
    location: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Локация",
    )
    source_chat_id: Mapped[int] = mapped_column(
        nullable=False,
        comment="ID Telegram-группы-источника",
    )
    source_message_id: Mapped[int] = mapped_column(
        nullable=False,
        comment="ID сообщения в группе",
    )
    category_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="ID категорий из classifier (может быть несколько)",
    )
