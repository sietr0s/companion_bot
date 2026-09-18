"""Ошибки модуля instagram_clients."""

from src.core.exceptions import (
    AppException,
    BadRequestError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)


class InstagramTwoFactorRequired(ConflictError):
    def __init__(self) -> None:
        super().__init__(detail="two_factor_required")


class InstagramChallengeRequired(ConflictError):
    def __init__(self) -> None:
        super().__init__(detail="challenge_required")


__all__ = [
    "AppException",
    "BadRequestError",
    "ConflictError",
    "InstagramChallengeRequired",
    "InstagramTwoFactorRequired",
    "NotFoundError",
    "UnauthorizedError",
    "ValidationError",
]
