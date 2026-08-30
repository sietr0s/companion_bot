"""LLM module specific exceptions."""

from src.core.exceptions import AppException, ValidationError


class LLMError(AppException):
    """Base exception for LLM errors."""

    pass


class GenerationError(LLMError):
    """Raised when text generation fails."""

    pass


class SummarizationError(LLMError):
    """Raised when summarization fails."""

    pass


class PromptNotFoundError(ValidationError):
    """Raised when prompt template is not found."""

    pass


class ProviderError(LLMError):
    """Raised when LLM provider fails."""

    pass
