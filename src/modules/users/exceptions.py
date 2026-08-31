"""Исключения модуля users."""

from src.core.exceptions import ConflictError, NotFoundError


class UserNotFoundError(NotFoundError):
    pass


class UserAlreadyExistsError(ConflictError):
    pass
