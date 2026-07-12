"""Схемы авторизации Telegram модуля telegram_clients."""

import uuid

from pydantic import BaseModel, Field

from src.modules.telegram_clients.constants import QrAuthStatus


class PhoneRequest(BaseModel):
    """Шаг 1: отправка номера телефона для получения SMS-кода."""

    phone: str = Field(max_length=20)


class CodeRequest(BaseModel):
    """Шаг 2: ввод SMS-кода подтверждения."""

    account_id: uuid.UUID
    code: str = Field(max_length=10)


class PasswordRequest(BaseModel):
    """Шаг 3: ввод пароля облачного шифрования (2FA)."""

    account_id: uuid.UUID
    password: str


class AuthStep1Response(BaseModel):
    """Ответ после отправки номера телефона."""

    account_id: uuid.UUID
    status: str = "code_sent"


class AuthStep2Response(BaseModel):
    """Ответ после ввода SMS-кода."""

    account_id: uuid.UUID
    status: str  # "connected" или "2fa_required"


class AuthStep3Response(BaseModel):
    """Ответ после ввода 2FA пароля."""

    account_id: uuid.UUID
    status: str = "connected"


class QrStartResponse(BaseModel):
    """Ответ на старт QR-авторизации."""

    account_id: uuid.UUID
    qr_url: str
    expires_at: float | None = None


class QrStatusResponse(BaseModel):
    """Текущий статус QR-сессии."""

    status: QrAuthStatus
    message: str | None = None
