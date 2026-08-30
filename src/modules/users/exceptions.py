"""Специфичные исключения модуля users."""

from src.core.exceptions import ConflictError, NotFoundError


class ProfileNotFoundError(NotFoundError):
    """Профиль пользователя не найден."""

    pass


class ProfileAlreadyExistsError(ConflictError):
    """Профиль пользователя уже существует."""

    pass


class TelegramAlreadyLinkedError(ConflictError):
    """Telegram уже привязан к другому пользователю."""

    pass


class TelegramNotFoundError(NotFoundError):
    """Telegram профиль не найден."""

    pass

