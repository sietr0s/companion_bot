"""HTTP API схемы для модуля users."""

import uuid

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Запрос на создание профиля пользователя."""

    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)


class UserUpdate(BaseModel):
    """Запрос на обновление профиля пользователя."""

    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(None, max_length=20)


class UserRead(BaseModel):
    """Ответ с данными профиля пользователя."""

    id: uuid.UUID
    auth_id: uuid.UUID
    first_name: str | None
    last_name: str | None
    email: str | None
    phone: str | None
    created_at: str
    updated_at: str | None

    class Config:
        from_attributes = True


class TelegramCreate(BaseModel):
    """Запрос на создание Telegram профиля."""

    telegram_id: int
    telegram_username: str | None = Field(None, max_length=100)
    telegram_first_name: str | None = Field(None, max_length=100)
    telegram_last_name: str | None = Field(None, max_length=100)


class TelegramRead(BaseModel):
    """Ответ с данными Telegram профиля."""

    id: uuid.UUID
    telegram_id: int
    telegram_username: str | None
    telegram_first_name: str | None
    telegram_last_name: str | None
    user_id: uuid.UUID | None

    class Config:
        from_attributes = True
