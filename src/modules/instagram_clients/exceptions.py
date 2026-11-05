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


# Preserve the existing public names used by routers and adapters.
InstagramTwoFactorRequired = InstagramTwoFactorRequiredError
InstagramChallengeRequired = InstagramChallengeRequiredError

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
