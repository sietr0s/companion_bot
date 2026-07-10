"""Публичные схемы модуля telegram_clients."""

from .account import AccountRead
from .auth import (
    AuthStep1Response,
    AuthStep2Response,
    AuthStep3Response,
    CodeRequest,
    PasswordRequest,
    PhoneRequest,
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
    "AccountRead",
    "ChatRead",
    "MediaItem",
    "MessageRead",
]
