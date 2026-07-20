"""Generate the frontend contract without exposing internal module endpoints."""

import json
import sys
from importlib import import_module
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "frontend" / "openapi.json"
FRONTEND_PATH_PREFIXES = ("/api/v1/public/", "/health")
FRONTEND_EXCLUDED_PATHS = {
    "/api/v1/public/auth/me",
    "/api/v1/public/auth/me/password",
}


def collect_schema_names(value: object, names: set[str]) -> None:
    """Collect component schemas reachable through local OpenAPI references."""
    if isinstance(value, dict):
        reference = value.get("$ref")
        prefix = "#/components/schemas/"
        if isinstance(reference, str) and reference.startswith(prefix):
            names.add(reference.removeprefix(prefix))
        for nested in value.values():
            collect_schema_names(nested, names)
    elif isinstance(value, list):
        for nested in value:
            collect_schema_names(nested, names)


def main() -> None:
    sys.path.insert(0, str(PROJECT_ROOT))
    app = import_module("src.main").app
    schema = app.openapi()
    schema["paths"] = {
        path: definition
        for path, definition in schema["paths"].items()
        if path.startswith(FRONTEND_PATH_PREFIXES)
        and path not in FRONTEND_EXCLUDED_PATHS
    }
    all_schemas = schema.get("components", {}).get("schemas", {})
    used_schemas: set[str] = set()
    collect_schema_names(schema["paths"], used_schemas)
    pending = list(used_schemas)
    while pending:
        schema_name = pending.pop()
        nested_names: set[str] = set()
        collect_schema_names(all_schemas.get(schema_name, {}), nested_names)
        for nested_name in nested_names - used_schemas:
            used_schemas.add(nested_name)
            pending.append(nested_name)
    schema["components"]["schemas"] = {
        name: definition
        for name, definition in all_schemas.items()
        if name in used_schemas
    }
    OUTPUT_PATH.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
