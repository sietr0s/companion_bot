"""Batching module exceptions."""

from src.core.exceptions import AppException, NotFoundError


class BatchError(AppException):
    """Base exception for batching module."""


class BatchNotFoundError(NotFoundError, BatchError):
    """Raised when a batch is not found."""


class BatchValidationError(BatchError):
    """Raised when batch validation fails."""

    def __init__(self, detail: str = "Validation error"):
        super().__init__(status_code=422, detail=detail)


class MessageLimitExceededError(BatchValidationError):
    """Raised when message limit in batch is exceeded."""
