"""Authentication for internal service-to-service HTTP endpoints."""

import secrets

from fastapi import Depends
from fastapi.security import APIKeyHeader

from src.core.config import settings
from src.core.exceptions import UnauthorizedError

INTERNAL_SERVICE_KEY_HEADER = "X-Internal-Service-Key"

internal_service_key_header = APIKeyHeader(
    name=INTERNAL_SERVICE_KEY_HEADER,
    auto_error=False,
)


async def require_internal_service_key(
    service_key: str | None = Depends(internal_service_key_header),
) -> None:
    """Require the configured service key for every internal endpoint."""
    if service_key is None or not secrets.compare_digest(service_key, settings.INTERNAL_SERVICE_KEY):
        raise UnauthorizedError(detail="Некорректный сервисный ключ")
