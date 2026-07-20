"""Tests for the common authentication guard on internal endpoints."""

from httpx import AsyncClient

from src.core.config import settings
from src.core.internal_auth import require_internal_service_key


class TestInternalAuthentication:
    async def test_internal_endpoint_rejects_missing_key(self, client: AsyncClient) -> None:
        client.headers.pop("X-Internal-Service-Key", None)
        response = await client.get("/internal/classifier/categories")

        assert response.status_code == 401

    async def test_internal_endpoint_rejects_invalid_key(self, client: AsyncClient) -> None:
        response = await client.get(
            "/internal/classifier/categories",
            headers={"X-Internal-Service-Key": "wrong-key"},
        )

        assert response.status_code == 401

    async def test_guard_accepts_configured_key(self) -> None:
        assert await require_internal_service_key(settings.INTERNAL_SERVICE_KEY) is None

    async def test_health_endpoint_does_not_require_internal_key(self, client: AsyncClient) -> None:
        response = await client.get("/health")

        assert response.status_code == 200
