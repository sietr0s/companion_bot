"""Константы модуля Telegram-клиентов."""

from enum import StrEnum


class TgAuthStatus(StrEnum):
    CODE_SENT = "code_sent"
    CONNECTED = "connected"
    TWO_FA_REQUIRED = "2fa_required"
    INVALID_CODE = "invalid_code"


class QrAuthStatus(StrEnum):
    PENDING = "pending"
    CONNECTED = "connected"
    EXPIRED = "expired"
    ERROR = "error"
