"""
Internal API-схемы модуля авторизации.

auth_id передаётся в теле запроса (для межмодульного взаимодействия).
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AuthRead(BaseModel):
    """Схема чтения учётной записи (для internal API)."""

    id: uuid.UUID
    identifier: str
    identifier_type: str
    hashed_password: str | None = None
    role: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AuthCreate(BaseModel):
    """Запрос на создание учётной записи (internal)."""

    identifier: str
    identifier_type: Literal["email", "phone", "telegram"]
    hashed_password: str
    role: str | None = None


class AuthUpdate(BaseModel):
    """Запрос на обновление учётной записи (internal)."""

    identifier: str | None = None
    identifier_type: Literal["email", "phone", "telegram"] | None = None
    hashed_password: str | None = None
    role: str | None = None


class ChangePasswordRequest(BaseModel):
    """Запрос на смену пароля (internal, с auth_id в body)."""

    auth_id: uuid.UUID
    current_password: str
    new_password: str = Field(min_length=8)


class DeleteAccountRequest(BaseModel):
    """Запрос на удаление учётной записи (internal, с auth_id в body)."""

    auth_id: uuid.UUID
    password: str


class VerifyTokenRequest(BaseModel):
    """Запрос на проверку токена (internal)."""

    token: str


class VerifyTokenResponse(BaseModel):
    """Ответ с информацией о токене (internal)."""

    valid: bool
    auth_id: uuid.UUID | None = None
    identifier: str | None = None
    role: str | None = None
