"""Внутренние схемы для модуля auth (internal API)."""

import uuid

from pydantic import BaseModel, Field


class AuthCreate(BaseModel):
    """Схема создания учётной записи (internal)."""

    identifier: str = Field(..., description="Email или телефон")
    identifier_type: str = Field(..., description="Тип идентификатора: 'email' или 'phone'")
    hashed_password: str
    role: str | None = None


class AuthRead(BaseModel):
    """Схема чтения учётной записи (internal)."""

    id: uuid.UUID
    identifier: str
    identifier_type: str
    role: str
    is_active: bool = True

    class Config:
        from_attributes = True


class AuthUpdate(BaseModel):
    """Схема обновления учётной записи (internal)."""

    identifier: str | None = None
    identifier_type: str | None = None
    role: str | None = None
    is_active: bool | None = None


class VerifyTokenRequest(BaseModel):
    """Запрос на проверку токена (internal)."""

    token: str


class VerifyTokenResponse(BaseModel):
    """Ответ проверки токена (internal)."""

    valid: bool
    auth_id: uuid.UUID | None = None
    role: str | None = None
