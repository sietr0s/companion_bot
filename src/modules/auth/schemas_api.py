"""HTTP API схемы для модуля auth."""

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """Запрос на регистрацию пользователя."""

    identifier: str = Field(..., description="Email или телефон")
    identifier_type: str = Field(..., description="Тип идентификатора: 'email' или 'phone'")
    password: str = Field(..., min_length=8, description="Пароль")


class LoginRequest(BaseModel):
    """Запрос на вход пользователя."""

    identifier: str = Field(..., description="Email или телефон")
    password: str = Field(..., description="Пароль")


class TokenResponse(BaseModel):
    """Ответ с JWT токеном."""

    access_token: str


class ChangePasswordRequest(BaseModel):
    """Запрос на смену пароля."""

    current_password: str
    new_password: str = Field(..., min_length=8)
