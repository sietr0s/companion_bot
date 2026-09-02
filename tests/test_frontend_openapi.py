"""Проверки отдельного OpenAPI-контракта frontend."""

import json
from pathlib import Path


def test_frontend_openapi_contains_no_internal_paths() -> None:
    schema_path = Path(__file__).parents[1] / "frontend" / "openapi.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["paths"]
    assert not any(path.startswith("/internal/") for path in schema["paths"])
    assert "/api/v1/public/users/" in schema["paths"]
    assert "/api/v1/public/telegram/" in schema["paths"]
    assert "/api/v1/public/memory/conversations/" in schema["paths"]
    assert "/api/v1/public/batches/" not in schema["paths"]
    assert "/api/v1/public/batch-messages/" not in schema["paths"]
    assert not any("/classifier" in path for path in schema["paths"])
    assert not any("/media" in path for path in schema["paths"])
    assert not any("/notifications" in path for path in schema["paths"])
    assert not any("/job-matcher" in path or "/job_matcher" in path for path in schema["paths"])
    assert "/api/v1/public/auth/me" not in schema["paths"]
    assert "/api/v1/public/auth/me/password" not in schema["paths"]
