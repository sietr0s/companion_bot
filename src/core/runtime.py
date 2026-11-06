"""Policy for operations that require AI models or external integrations."""

from src.core.config import settings
from src.core.exceptions import AppException


def require_external_services() -> None:
    if settings.SAFE_MODE:
        raise AppException(
            status_code=503,
            detail="External integrations and AI are disabled in SAFE_MODE",
        )
