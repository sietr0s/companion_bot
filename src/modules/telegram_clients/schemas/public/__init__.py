"""Публичные схемы модуля telegram_clients."""

from .account import AccountRead
from .auth import (
    AuthStep1Response,
    AuthStep2Response,
    AuthStep3Response,
    CodeRequest,
    PasswordRequest,
    PhoneRequest,
    QrStartResponse,
    QrStatusResponse,
)
from .chat import ChatRead
from .media import MediaItem
from .message import MessageRead

__all__ = [
    "PhoneRequest",
    "CodeRequest",
    "PasswordRequest",
    "AuthStep1Response",
    "AuthStep2Response",
    "AuthStep3Response",
    "QrStartResponse",
    "QrStatusResponse",
    "AccountRead",
    "ChatRead",
    "MediaItem",
    "MessageRead",
]
