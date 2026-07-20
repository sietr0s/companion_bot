---
name: openapi-frontend-generation
description: How to regenerate the frontend TypeScript API client from backend OpenAPI schema — update openapi.json then run npm run generate:api; never edit generated files manually.
source: auto-skill
extracted_at: '2026-07-12T19:37:13.700Z'
---

# OpenAPI → Frontend API Client Generation

**Project:** micromonolit
**Tool:** `openapi-typescript-codegen` (v0.29.0)

## Workflow

When adding new backend routes or schemas that the frontend needs to call:

1. **Update `frontend/openapi.json`** — add new paths under `"paths"` and new schemas under `"components" > "schemas"`. Match the existing structure exactly (operationId, tags, parameters, responses, security).

2. **Regenerate the TypeScript client:**
   ```bash
   cd frontend && npm run generate:api
   ```
   This runs: `openapi --input ./openapi.json --output ./src/api/generated --client fetch --useUnionTypes`

3. **Never edit generated files manually.** All files under `frontend/src/api/generated/` are auto-generated and marked `/* generated using openapi-typescript-codegen -- do not edit */`.

## openapi.json structure conventions

- Paths use the full FastAPI route (e.g. `/api/v1/public/telegram/auth/qr`)
- `operationId` uses snake_case matching the Python function name (e.g. `auth_qr_start_api_v1_public_telegram_auth_qr_post`)
- UUID parameters: `"type": "string", "format": "uuid"`
- Optional fields: `"anyOf": [{"type": "..."}, {"type": "null"}]`
- Enum fields: `"enum": ["value1", "value2"]`
- Security: `"security": [{"HTTPBearer": []}]` for JWT-protected routes

## Alternative: regenerate from running backend

If the backend is runnable locally:
```bash
python -c "from src.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > frontend/openapi.json
```
Then run `npm run generate:api`. This requires all Python dependencies installed.
