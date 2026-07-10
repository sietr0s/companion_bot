"""
Модели модуля classifier.

Category — категории для классификации текстов.
ClassificationLog — лог классификации текстов.
"""

import uuid

from sqlalchemy import JSON, Boolean, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from src.base.model import BaseModel


class Category(BaseModel):
    """
    Категория для классификации текстов.

    name — уникальное имя категории.
    slug — уникальный слаг (используется в API).
    description — описание категории.
    is_active — флаг активности (неактивные не участвуют в классификации).
    """

    __tablename__ = "classifier_category"

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )


class ClassificationLog(BaseModel):
    """
    Лог классификации текста.

    text_hash — SHA256 хэш текста (для дедупликации).
    text_preview — первые 200 символов текста.
    category_slug — слаг категории (топ-1 по confidence).
    confidence — уверенность модели (топ-1).
    entities — извлечённые сущности (JSON).
    request_id — UUID запроса (для корреляции).
    """

    __tablename__ = "classifier_log"

    text_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )
    text_preview: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    category_slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    entities: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )
