"""Контракт: модули владеют полными URL-префиксами своих роутеров."""

from src.main import app


def test_module_router_prefixes() -> None:
    paths = set(app.openapi()["paths"])

    expected_paths = {
        "/api/v1/public/auth/register",
        "/internal/auth/",
        "/api/v1/public/users/me",
        "/api/v1/public/users/{profile_id}",
        "/internal/users/",
        "/api/v1/public/notifications/templates/",
        "/internal/notifications/send",
        "/api/v1/public/telegram/",
        "/internal/telegram/{account_id}/settings",
        "/api/v1/public/media/upload",
        "/internal/media/upload",
        "/api/v1/public/media/",
        "/api/v1/public/classifier/categories",
        "/internal/classifier/categories",
        "/internal/job-matcher/subscriptions",
        "/api/v1/public/job-matcher/subscriptions",
        "/api/v1/public/job-matcher/offers",
        "/api/v1/public/job-matcher/users/{auth_id}",
    }

    assert expected_paths <= paths
    assert not any("/internal/classifier/internal/classifier" in path for path in paths)
