"""Memory module specific exceptions."""

from src.core.exceptions import NotFoundError, ValidationError


class ConversationNotFoundError(NotFoundError):
    """Raised when conversation is not found."""

    pass


class MessageNotFoundError(NotFoundError):
    """Raised when message is not found."""

    pass


class BatchValidationError(ValidationError):
    """Raised when batch validation fails."""

    pass


class ContextBuildError(Exception):
    """Raised when context building fails."""

    pass
