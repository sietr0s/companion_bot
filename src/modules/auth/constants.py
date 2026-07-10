"""
Константы модуля авторизации.

Централизованное хранение всех констант и перечислений,
используемых в модуле auth.
"""

from enum import StrEnum


class IdentifierType(StrEnum):
    """Типы идентификаторов для аутентификации."""

    EMAIL = "email"
    PHONE = "phone"
    TELEGRAM = "telegram"


# Сообщения об ошибках
ERROR_MESSAGES = {
    "duplicate_identifier": "Пользователь с таким {identifier_type} уже существует",
    "invalid_credentials": "Неверный идентификатор или пароль",
}
