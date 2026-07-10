"""
Базовая модель для всех сущностей проекта.

Все модели наследуются от BaseModel, который обеспечивает
единый набор служебных полей (id, created_at, updated_at).
Это позволяет при выносе модуля в микросервис сохранить
совместимую структуру данных.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# Единый declarative base для всего проекта.
# Объявляется как класс-наследник DeclarativeBase (SQLAlchemy 2.0 style).
# Все модели привязаны к одному Base, чтобы Alembic мог управлять миграциями.
class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    """Абстрактная базовая модель с общими полями для всех сущностей."""

    __abstract__ = True

    # UUID как первичный ключ — обеспечивает глобальную уникальность,
    # что важно при потенциальном разделении на микросервисы
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # server_default=func.now() — СУБД ставит таймстамп, а не Python.
    # Это гарантирует консистентность времени при конкурентных записях.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # onupdate=func.now() — автоматическое обновление при каждом UPDATE
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
