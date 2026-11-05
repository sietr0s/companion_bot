"""Публичные HTTP-схемы модуля auth."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

TELEGRAM_USERNAME_RE = re.compile(r"^@?[A-Za-z][A-Za-z0-9_]{4,31}$")


class RegisterRequest(BaseModel):
    identifier: str
    identifier_type: str
    password: str = Field(..., min_length=8)

    @model_validator(mode="after")
    def validate_telegram_identifier(self) -> "RegisterRequest":
        if self.identifier_type != "telegram":
            return self
        value = self.identifier
        username = value.lstrip("@")
        if len(username) < 5 or len(username) > 32:
            raise ValueError("от 5 до 32 символов")
        if username[:1].isdigit():
            raise ValueError("не может начинаться с цифры")
        if not TELEGRAM_USERNAME_RE.match(value):
            raise ValueError("только буквы, цифры и подчеркивание")
        return self


class LoginRequest(BaseModel):
    identifier: str
    password: str
    identifier_type: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthAccountCreate(BaseModel):
    identifier: str
    identifier_type: str
    hashed_password: str
    role: str = "user"


class AuthAccountUpdate(BaseModel):
    identifier: str | None = None
    identifier_type: str | None = None
    hashed_password: str | None = None
    role: str | None = None


class AuthAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier: str
    identifier_type: str
    role: str
    created_at: datetime
    updated_at: datetime
