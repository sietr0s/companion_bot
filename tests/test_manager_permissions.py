"""Every manager access level enforces the shared admin JWT policy."""

import pytest
from fastapi.routing import APIRoute

from src.core.dependencies import get_current_admin
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


def test_every_manager_route_inherits_the_same_permission_dependency():
    def dependencies(node):
        yield node.call
        for child in node.dependencies:
            yield from dependencies(child)

    for route in app.routes:
        if isinstance(route, APIRoute) and ".routers.manager" in route.endpoint.__module__:
            assert get_current_admin in dependencies(route.dependant), route.path
