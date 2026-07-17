"""
Перечисления модуля авторизации.

Централизованное хранение всех перечислений,
используемых в модуле auth.
"""

from enum import StrEnum


class IdentifierType(StrEnum):
    """Типы идентификаторов для аутентификации."""

    EMAIL = "email"
    PHONE = "phone"
    TELEGRAM = "telegram"
