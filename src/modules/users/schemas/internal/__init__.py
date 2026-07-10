"""Internal схемы модуля users."""

from .telegram import (
    TelegramCreate,
    TelegramRead,
    TelegramUpdate,
)
from .user import (
    UserCreate,
    UserRead,
    UserUpdate,
)

__all__ = [
    "UserRead",
    "UserCreate",
    "UserUpdate",
    "TelegramRead",
    "TelegramCreate",
    "TelegramUpdate",
]
