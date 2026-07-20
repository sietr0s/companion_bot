"""Tests for the shared internal HTTP client."""

import httpx
import respx

from src.core.clients.base import BaseHTTPClient
from src.core.internal_auth import INTERNAL_SERVICE_KEY_HEADER


class TestBaseHTTPClient:
    @respx.mock
    async def test_adds_internal_service_key_header(self) -> None:
        route = respx.get("http://internal.test/resource").mock(
            return_value=httpx.Response(200, json={"ok": True}),
        )

        response = await BaseHTTPClient(base_url="http://internal.test").get("/resource")

        assert response is not None
        assert response.json() == {"ok": True}
        assert route.calls.last.request.headers[INTERNAL_SERVICE_KEY_HEADER]
