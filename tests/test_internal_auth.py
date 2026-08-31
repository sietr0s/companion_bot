"""Internal HTTP API отключён: маршрутов /internal/ нет."""

from httpx import AsyncClient

from src.main import app


class TestNoInternalApi:
    async def test_internal_paths_are_absent(self, client: AsyncClient) -> None:
        response = await client.get("/internal/users/")
        assert response.status_code == 404

    async def test_openapi_has_no_internal_paths(self) -> None:
        paths = app.openapi()["paths"]
        assert not any(path.startswith("/internal/") for path in paths)

    async def test_health_endpoint_is_public(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        assert response.status_code == 200
