"""
Модель учётной записи авторизации.

Auth — отдельная модель от User.
Это разделение позволяет модулю auth работать независимо:
при выносе в микросервис auth не нужен доступ к данным профиля.
"""

import uuid

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.base.model import BaseModel


class Auth(BaseModel):
    """
    Учётная запись авторизации.

    Хранит identifier (email или phone), хэш пароля и роль (user/admin).
    Поддерживает аутентификацию по email ИЛИ phone через единое поле identifier.
    Данные профиля (имя, аватар и т.д.) — в модуле users.
    """

    __tablename__ = "auth"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    identifier: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    identifier_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="user",
    )
