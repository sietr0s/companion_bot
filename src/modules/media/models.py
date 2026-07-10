"""
Модель хранимого файла.

Файл — независимая сущность без привязки к владельцам.
Модули-потребители хранят file_id в своих таблицах.
is_public определяет доступность через публичный роут.
"""

import uuid

from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from src.base.model import BaseModel


class StoredFile(BaseModel):
    """
    Хранимый файл.

    storage_key — путь/ключ в хранилище (sharded для FS).
    is_public — если True, файл доступен через публичный роут без JWT.
    """

    __tablename__ = "stored_file"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    storage_key: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
