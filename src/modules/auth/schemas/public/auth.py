"""
Публичные API-схемы модуля авторизации.

auth_id передаётся через JWT токен (header Authorization).
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RegisterRequest(BaseModel):
    """Запрос на регистрацию нового пользователя."""

    identifier: str
    identifier_type: Literal["email", "phone", "telegram"]
    password: str = Field(min_length=8)

    @model_validator(mode="after")
    def validate_identifier(self):
        """Валидация identifier в зависимости от типа."""
        v = self.identifier
        identifier_type = self.identifier_type

        if identifier_type == "email":
            if "@" not in v or "." not in v.split("@")[-1]:
                raise ValueError("Неверный формат email")
        elif identifier_type == "phone":
            if not v.startswith("+") and not v.startswith("8"):
                raise ValueError("Телефон должен начинаться с + или 8")
            phone_digits = v[1:] if v.startswith("+") else v[1:] if v.startswith("8") else v
            if not phone_digits.isdigit():
                raise ValueError("Телефон должен содержать только цифры после префикса")
        elif identifier_type == "telegram":
            username = v.lstrip("@")
            if len(username) < 5 or len(username) > 32:
                raise ValueError("Telegram username должен быть от 5 до 32 символов")
            if not username.replace("_", "").isalnum():
                raise ValueError(
                    "Telegram username может содержать только буквы, цифры и подчеркивание"
                )
            if username[0].isdigit():
                raise ValueError("Telegram username не может начинаться с цифры")
        return self


class LoginRequest(BaseModel):
    """Запрос на авторизацию."""

    identifier: str
    password: str


class TokenResponse(BaseModel):
    """Ответ с JWT-токеном."""

    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    """Запрос на смену пароля."""

    current_password: str
    new_password: str = Field(min_length=8)
