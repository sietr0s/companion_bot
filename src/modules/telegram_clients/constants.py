"""
Константы модуля Telegram-клиентов.
"""

from enum import StrEnum


class TgAuthStatus(StrEnum):
    """Статусы авторизации в Telegram."""

    CODE_SENT = "code_sent"
    CONNECTED = "connected"
    TWO_FA_REQUIRED = "2fa_required"
    INVALID_CODE = "invalid_code"


class QrAuthStatus(StrEnum):
    """Статусы QR-авторизации."""

    PENDING = "pending"
    CONNECTED = "connected"
    EXPIRED = "expired"
    ERROR = "error"


class ChatType(StrEnum):
    """Типы чатов в Telegram."""

    PRIVATE = "private"
    GROUP = "group"
    CHANNEL = "channel"
    SUPERGROUP = "supergroup"


class MediaType(StrEnum):
    """Типы медиа в Telegram сообщениях."""

    PHOTO = "photo"
    VIDEO = "video"
    VOICE = "voice"
    DOCUMENT = "document"
    AUDIO = "audio"


# Сообщения об ошибках
ERROR_MESSAGES = {
    "account_not_found": "Аккаунт не найден",
    "account_not_connected": "Аккаунт не подключён",
    "account_not_yours": "Аккаунт не найден",
    "session_file_not_found": "Session файл не найден",
}
