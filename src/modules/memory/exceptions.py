"""Memory module specific exceptions."""

from src.core.exceptions import AppException, NotFoundError, ValidationError


class ConversationNotFoundError(NotFoundError):
    """Raised when conversation is not found."""

    pass


class MessageNotFoundError(NotFoundError):
    """Raised when message is not found."""

    pass


class BatchValidationError(ValidationError):
    """Raised when batch validation fails."""

    pass


class ContextBuildError(AppException):
    """Raised when context building fails."""

    def __init__(self, detail: str = "Не удалось собрать контекст"):
        super().__init__(status_code=500, detail=detail)
