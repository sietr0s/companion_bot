"""Example module - базовый модуль с CRUD операциями."""

from src.base.model import BaseModel
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class ExampleModel(BaseModel):
    """Модель примера."""

    __tablename__ = "examples"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
