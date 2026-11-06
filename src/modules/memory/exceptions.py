"""Memory errors exposed by command handling."""

from src.core.exceptions import NotFoundError


class ConversationNotFoundError(NotFoundError):
    """An outgoing-memory update references a missing conversation."""
