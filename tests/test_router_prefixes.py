"""Контракт: модули владеют полными URL-префиксами своих роутеров. Internal API нет."""

from src.main import app


def test_module_router_prefixes() -> None:
    paths = set(app.openapi()["paths"])

    expected_paths = {
        "/api/v1/public/auth/register",
        "/api/v1/public/auth/login",
        "/api/v1/public/users/",
        "/api/v1/public/telegram/",
        "/api/v1/public/instagram/accounts/",
        "/api/v1/public/memory/conversations/",
    }

    assert expected_paths <= paths
    assert not any(path.startswith("/internal/") for path in paths)
