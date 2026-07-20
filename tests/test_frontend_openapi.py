"""Проверки отдельного OpenAPI-контракта frontend."""

import json
from pathlib import Path


def test_frontend_openapi_contains_no_internal_paths() -> None:
    schema_path = Path(__file__).parents[1] / "frontend" / "openapi.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["paths"]
    assert not any(path.startswith("/internal/") for path in schema["paths"])
    assert "/api/v1/public/users/" in schema["paths"]
    assert "/api/v1/public/job-matcher/subscriptions" in schema["paths"]
    assert "/api/v1/public/job-matcher/offers" in schema["paths"]
    assert "/api/v1/public/media/" in schema["paths"]
    assert "/api/v1/public/auth/me" not in schema["paths"]
    assert "/api/v1/public/auth/me/password" not in schema["paths"]
