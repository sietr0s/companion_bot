"""Each module subclasses this abstract row into its own table."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from src.base.model import Base


class BaseConfigModel(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(
        Integer, CheckConstraint("id = 1"), primary_key=True, default=1, autoincrement=False
    )
    revision: Mapped[int] = mapped_column(default=0, nullable=False)
    overrides: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[UUID | None] = mapped_column(nullable=True)
