"""Orchestrator module specific exceptions."""

from src.core.exceptions import AppException, NotFoundError


class OrchestratorError(AppException):
    """Base exception for orchestrator errors."""

    pass


class UseCaseNotFoundError(NotFoundError):
    """Raised when use case handler is not found."""

    pass


class CorrelationStateError(OrchestratorError):
    """Raised when correlation state is invalid or missing."""

    pass


class EventRoutingError(OrchestratorError):
    """Raised when event routing fails."""

    pass
