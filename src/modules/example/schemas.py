"""Схемы для Example модуля (API)."""

from pydantic import BaseModel, Field


class ExampleBase(BaseModel):
    """Базовая схема для Example."""

    name: str = Field(..., min_length=1, max_length=255, description="Название")
    description: str | None = Field(None, max_length=1000, description="Описание")


class ExampleCreate(ExampleBase):
    """Схема для создания Example."""

    pass


class ExampleUpdate(BaseModel):
    """Схема для обновления Example."""

    name: str | None = Field(None, min_length=1, max_length=255, description="Название")
    description: str | None = Field(None, max_length=1000, description="Описание")


class ExampleRead(ExampleBase):
    """Схема для чтения Example."""

    id: int
    created_at: str
    updated_at: str | None

    class Config:
        from_attributes = True
