"""Ошибки модуля instagram_clients."""

from src.core.exceptions import (
    AppException,
    BadRequestError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)


class InstagramTwoFactorRequiredError(ConflictError):
    def __init__(self) -> None:
        super().__init__(detail="two_factor_required")


class InstagramChallengeRequiredError(ConflictError):
    def __init__(self) -> None:
        super().__init__(detail="challenge_required")


__all__ = [
    "AppException",
    "BadRequestError",
    "ConflictError",
    "InstagramChallengeRequiredError",
    "InstagramTwoFactorRequiredError",
    "NotFoundError",
    "UnauthorizedError",
    "ValidationError",
]
