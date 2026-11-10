"""Every manager access level enforces the shared admin JWT policy."""

import re

import pytest

from src.main import app

MANAGER_PATHS = [
    "/api/v1/public/auth/accounts/",
    "/api/v1/public/users/",
    "/api/v1/public/telegram/accounts/",
    "/api/v1/public/instagram/accounts/",
    "/api/v1/public/memory/conversations/",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("path", MANAGER_PATHS)
async def test_manager_endpoints_reject_missing_or_non_admin_tokens(api_client, auth_token, path):
    anonymous = await api_client.get(path)
    assert anonymous.status_code == 401
    user = await api_client.get(path, headers={"Authorization": f"Bearer {auth_token}"})
    assert user.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("path", MANAGER_PATHS)
async def test_manager_endpoints_allow_admin_tokens(api_client, admin_token, path):
    response = await api_client.get(path, headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_every_manager_operation_rejects_anonymous_and_non_admin_requests(
    api_client, auth_token
):
    operations = []
    for path, methods in app.openapi()["paths"].items():
        if not path.startswith("/api/v1/public/"):
            continue
        if path in {
            "/api/v1/public/auth/login",
            "/api/v1/public/auth/register",
            "/api/v1/public/auth/me",
            "/api/v1/public/auth/me/password",
        }:
            continue
        url = re.sub(r"\{[^}]+\}", "00000000-0000-0000-0000-000000000001", path)
        for method in methods:
            if method in {"get", "post", "put", "patch", "delete"}:
                operations.append((method, url))
    assert operations, "Permission test must actually exercise manager endpoints"
    for method, url in operations:
        anonymous = await api_client.request(method, url, json={})
        assert anonymous.status_code == 401, (method, url, anonymous.text)
        user = await api_client.request(
            method, url, json={}, headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert user.status_code == 403, (method, url, user.text)
